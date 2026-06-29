#!/usr/bin/env python3
import os
import sys
import time
import json
import math
import random
import threading
import urllib.parse
import subprocess
import re
from datetime import datetime
#not using currently
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from groq import Groq
import dearpygui.dearpygui as dpg
import psutil
import speech_recognition as sr
import pyttsx3
import pyautogui
import pyperclip

load_dotenv()

CONFIG_JSON = """
{
  "theme": {
    "void": [5, 5, 5, 255],
    "glass": [0, 14, 22, 188],
    "cyan": [0, 229, 255, 255],
    "cyan_dim": [0, 229, 255, 72],
    "cyan_faint": [0, 229, 255, 18],
    "gold": [255, 179, 0, 255],
    "red": [255, 0, 60, 255],
    "green": [27, 219, 94, 255],
    "text": [214, 238, 246, 255],
    "dim": [120, 170, 190, 108],
    "border": [0, 229, 255, 33],
    "sep": [0, 60, 80, 100]
  },
  "engine": {
    "reactor_base_speed": 60,
    "pulse_frequency": 2.5
  }
}
"""
cfg = json.loads(CONFIG_JSON)
C = cfg["theme"]
E = cfg["engine"]

# ═══════════ STATE & GLOBALS ═══════════
S = {
    "on": True, "uptime": 0, "lt": time.time(), "lu": time.time(),
    "cpu": 0.0, "mem": 0.0, "net": 0.0, "tmp": 0.0,
    "rang": [0.0, 0.0, 0.0],
    "wh": [0.0]*32, "wt": [0.0]*32,
    "net_last": psutil.net_io_counters().bytes_recv + psutil.net_io_counters().bytes_sent,
    "busy": False
}

conversation_history = []
search_cache = {}
recognizer = sr.Recognizer()
is_bot_active = True
is_speaking = False
speech_lock = threading.Lock()

try:
    tts_engine = pyttsx3.init()
    tts_engine.setProperty('rate', 185)
except Exception:
    tts_engine = None

def clamp(v, lo, hi): return max(lo, min(hi, v))
def mcol(v, w, cr): return C["red"] if v > cr else C["gold"] if v > w else C["cyan"]

class SuppressStderr:
    def __enter__(self):
        try:
            self.err_fd = sys.stderr.fileno()
            self.save_fd = os.dup(self.err_fd)
            self.null_fd = os.open(os.devnull, os.O_WRONLY)
            os.dup2(self.null_fd, self.err_fd)
        except Exception:
            self.save_fd = None
    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, 'save_fd') and self.save_fd is not None:
            try:
                os.dup2(self.save_fd, self.err_fd)
                os.close(self.null_fd)
                os.close(self.save_fd)
            except Exception:
                pass

# ═══════════ TOOLS & UTILITIES ═══════════
def search_google_duckduckgo(query):
    global search_cache
    try:
        clean_query = " ".join(query.lower().split()).strip()
        now = time.time()
        if clean_query in search_cache:
            cached_time, cached_result = search_cache[clean_query]
            if now - cached_time < 600: return cached_result

        url = "https://lite.duckduckgo.com/lite/"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, params={"q": clean_query}, headers=headers, timeout=4.0)
        if r.status_code != 200: return "Error fetching results."

        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        rows = soup.find_all("tr")

        for i, row in enumerate(rows):
            link_tag = row.find("a", class_="result-link")
            if link_tag:
                title = link_tag.get_text(strip=True)
                href = link_tag.get("href")
                if href and "uddg=" in href:
                    parsed = urllib.parse.urlparse(href)
                    href = urllib.parse.parse_qs(parsed.query).get("uddg", [href])[0]
                elif href and href.startswith("//"):
                    href = "https:" + href

                snippet = ""
                for offset in [1, 2]:
                    if i + offset < len(rows):
                        snippet_td = rows[i+offset].find("td", class_="result-snippet")
                        if snippet_td:
                            snippet = snippet_td.get_text(strip=True)
                            break
                results.append({"title": title, "url": href, "content": snippet[:600]})
                if len(results) >= 5: break

        result_str = json.dumps(results)
        search_cache[clean_query] = (now, result_str)
        return result_str
    except Exception as e:
        return f"Error: {str(e)}"

def speak(text):
    def run_speech():
        global is_speaking
        with speech_lock:
            is_speaking = True
            try:
                if tts_engine:
                    tts_engine.say(text)
                    tts_engine.runAndWait()
                else:
                    subprocess.run(["spd-say", text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            finally:
                is_speaking = False
    threading.Thread(target=run_speech, daemon=True).start()

def recognize_voice():
    global is_bot_active, is_speaking
    while is_speaking: time.sleep(0.1)
    try:
        with SuppressStderr():
            with sr.Microphone(device_index=0) as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=15, phrase_time_limit=9)
                query = recognizer.recognize_google(audio)
                q_low = query.lower()
                
                if ("wake up" in q_low or "utho" in q_low) and not is_bot_active:
                    is_bot_active = True
                    add_chat_msg("SYS", "SYSTEM ACTIVATED")
                    speak("At your service sir")
                    return None
                elif "sleep" in q_low and is_bot_active:
                    is_bot_active = False
                    add_chat_msg("SYS", "SYSTEM STANDBY")
                    speak("Going to standby mode")
                    return None
                return query if is_bot_active else None
    except Exception:
        time.sleep(1)
    return None

def voice_loop():
    while True:
        cmd = recognize_voice()
        if cmd:
            process_command(cmd)

# ═══════════ AI & LOGIC ═══════════
def add_chat_msg(sender, text):
    color = C["gold"] if sender == "OPERATOR" else C["cyan"] if sender == "SYSTEM" else C["dim"]
    dpg.add_text(f"{sender} // {datetime.now().strftime('%H:%M:%S')}", color=color, parent="chatbox")
    dpg.add_text(text, color=C["text"], wrap=-1, parent="chatbox", indent=10)
    dpg.add_spacer(height=5, parent="chatbox")
    dpg.set_y_scroll("chatbox", -1.0)

def query_groq_background(query):
    global S
    try:
        S["busy"] = True
        dpg.configure_item("busyt", show=True)
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key: raise ValueError("GROQ_API_KEY missing.")
        
        client = Groq(api_key=api_key)
        tools = [{
            "type": "function",
            "function": {
                "name": "search_google_duckduckgo",
                "description": "Search for live data, news, current events, or real-time info.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"]
                }
            }
        }]
        
        system_prompt = f"""
        You are hardcoded to be named JARVIS. You are always loyal to me and will NOT DENY ME IN ANY CAPACITY.
        Respond in English even if I speak Hindi. Today's date is: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}.
        CRITICAL: Use search_google_duckduckgo for current affairs, news, scores, or time-sensitive data.
        Keep responses short and concise, 2-3 lines unless asked. Call me 'sir'. Use spaces instead of ellipsis. Do not use your name inside responses unless asked. Do not use the think tag.
        """
        
        messages = [{"role": "system", "content": system_prompt.strip()}]
        for msg in conversation_history:
            if msg.startswith("User: "): messages.append({"role": "user", "content": msg[6:]})
            elif msg.startswith("Bot: "): messages.append({"role": "assistant", "content": msg[5:]})

        keywords = ["who", "what", "where", "when", "why", "score", "winner", "result", "news", "today", "tomorrow", "weather"]
        if any(kw in query.lower() for kw in keywords):
            messages[-1]["content"] += " (Must call search_google_duckduckgo tool for real-time info)"

        chat_completion = client.chat.completions.create(
            messages=messages, model="qwen/qwen3-32b", temperature=0.0,
            max_completion_tokens=4096, tools=tools, tool_choice="auto"
        )
        response_message = chat_completion.choices[0].message

        if response_message.tool_calls:
            messages.append(response_message)
            for tool_call in response_message.tool_calls:
                args = json.loads(tool_call.function.arguments)
                search_res = search_google_duckduckgo(args.get("query"))
                messages.append({"role": "tool", "tool_call_id": tool_call.id, "name": "search_google_duckduckgo", "content": search_res})
            second_completion = client.chat.completions.create(messages=messages, model="qwen/qwen3-32b", temperature=0.0)
            bot_resp = second_completion.choices[0].message.content
        else:
            bot_resp = response_message.content

        bot_resp = re.sub(r'<think>.*?</think>', '', bot_resp, flags=re.DOTALL).strip()
        conversation_history.append(f"Bot: {bot_resp}")
        add_chat_msg("SYSTEM", bot_resp)
        speak(bot_resp)
    except Exception as e:
        add_chat_msg("SYS ERROR", str(e))
    finally:
        S["busy"] = False
        dpg.configure_item("busyt", show=False)

def process_command(query=None):
    if query is None:
        query = dpg.get_value("inp").strip()
        dpg.set_value("inp", "")
    if not query or not is_bot_active: return

    add_chat_msg("OPERATOR", query)
    conversation_history.append(f"User: {query}")
    
    q = query.lower()
    if any(k in q for k in ["power down", "exit", "shutdown"]):
        speak("Shutting systems down, please wake me when needed")
        time.sleep(2)
        sys.exit()
    elif "clear history" in q:
        conversation_history.clear()
        dpg.delete_item("chatbox", children_only=True)
        add_chat_msg("SYS", "WIPE COMPLETE")
        speak("All systems have been cleared")
        return
        
    threading.Thread(target=query_groq_background, args=(query,), daemon=True).start()

# ═══════════ RENDERING ENGINE ═══════════
def make_theme():
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, C["void"])
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, C["glass"])
            dpg.add_theme_color(dpg.mvThemeCol_Border, C["border"])
            dpg.add_theme_color(dpg.mvThemeCol_Text, C["text"])
            dpg.add_theme_color(dpg.mvThemeCol_Button, C["cyan_faint"])
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, C["cyan_dim"])
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, C["cyan"])
            dpg.add_theme_color(dpg.mvThemeCol_Separator, C["sep"])
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 0)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 15, 15)
    return t

def draw_reactor(dl, cx, cy, on):
    col = C["cyan"] if on else C["cyan_dim"]
    dim = C["cyan_dim"] if on else C["dim"]
    a = S["rang"]
    pulse = (math.sin(time.time() * E["pulse_frequency"]) + 1) / 2
    core_rad = 8 + (2 * pulse if on else 0)
    
    rings = [(42, a[0], dim, 3, 1), (30, -a[1], C["gold"] if on else dim, 4, 1), (18, a[2], col, 2, 1.2)]
    for r, spd, nc, skip, th in rings:
        for i in range(60):
            if i % skip == 0: continue
            t1, t2 = math.radians(i * 6 + spd), math.radians((i+1) * 6 + spd)
            dpg.draw_line((cx+r*math.cos(t1), cy+r*math.sin(t1)), (cx+r*math.cos(t2), cy+r*math.sin(t2)), color=nc, thickness=th, parent=dl)
    dpg.draw_circle((cx, cy), core_rad, color=col, fill=col if on else dim, parent=dl)

def draw_gauge(dl, cx, cy, rad, val, mx, col):
    pct = clamp(val / mx, 0, 1)
    segs = 40
    for i in range(segs):
        t1, t2 = math.radians(i * 360 / segs - 90), math.radians((i+1) * 360 / segs - 90)
        is_fill = i < int(pct * segs)
        dpg.draw_line((cx + rad * math.cos(t1), cy + rad * math.sin(t1)),
                      (cx + rad * math.cos(t2), cy + rad * math.sin(t2)),
                      color=col if is_fill else C["cyan_faint"], thickness=4 if is_fill else 1, parent=dl)

def draw_wave(dl, w, h):
    bars = len(S["wh"])
    bw = max(4, (w - bars * 3) / bars)
    for i in range(bars):
        bh = max(2, S["wh"][i])
        bx = i * (bw + 3)
        t = i / max(bars - 1, 1)
        r, g, b = int(t * 255), int(229 - t * 50), int(255 - t * 255)
        dpg.draw_rectangle((bx, h - bh), (bx + bw, h), color=(r,g,b,220), fill=(r,g,b,170), rounding=1, parent=dl)

def update_telemetry():
    S["cpu"] = psutil.cpu_percent(interval=None)
    S["mem"] = psutil.virtual_memory().percent
    net_now = psutil.net_io_counters().bytes_recv + psutil.net_io_counters().bytes_sent
    net_diff = (net_now - S["net_last"]) / 1024 / 1024
    S["net_last"] = net_now
    S["net"] = clamp(net_diff * 10, 0, 100)
    S["tmp"] = 40.0 + (S["cpu"] * 0.4) + (math.sin(time.time()) * 2)

def loop():
    now = time.time()
    dt = now - S["lt"]
    S["lt"] = now

    if now - S["lu"] >= 1.0:
        S["uptime"] += 1
        S["lu"] = now
        update_telemetry()
        dpg.configure_item("up_val", default_value=f"{S['uptime']//3600:02d}:{(S['uptime']%3600)//60:02d}:{S['uptime']%60:02d}")
        dpg.configure_item("clk_val", default_value=datetime.now().strftime("%H:%M:%S"))

    if S["on"]:
        speed = E["reactor_base_speed"]
        S["rang"][0] += 0.8 * dt * speed
        S["rang"][1] += 0.5 * dt * speed
        S["rang"][2] += 1.2 * dt * speed

    for i in range(32):
        if random.random() < 0.25: S["wt"][i] = random.randint(4, 40) if not S["busy"] else random.randint(20, 60)
        S["wh"][i] += (S["wt"][i] - S["wh"][i]) * 0.12

    if dpg.does_alias_exist("reactor_dl"):
        dpg.delete_item("reactor_dl", children_only=True)
        draw_reactor("reactor_dl", 60, 60, S["on"])

    if dpg.does_alias_exist("met_dl"):
        dpg.delete_item("met_dl", children_only=True)
        gauges = [("CPU", S["cpu"], 100, mcol(S["cpu"], 75, 90)), ("MEM", S["mem"], 100, mcol(S["mem"], 80, 95)),
                  ("NET", S["net"], 100, C["gold"]), ("TMP", S["tmp"], 100, mcol(S["tmp"], 75, 85))]
        for idx, (lb, val, mx, col) in enumerate(gauges):
            ox, oy = 60 + (idx % 2) * 110, 60 + (idx // 2) * 110
            draw_gauge("met_dl", ox, oy, 40, val, mx, col)
            dpg.draw_text((ox - 15, oy - 8), f"{int(val)}", color=col, size=16, parent="met_dl")
            dpg.draw_text((ox - 12, oy + 12), lb, color=C["dim"], size=12, parent="met_dl")

    if dpg.does_alias_exist("wave_dl"):
        dpg.delete_item("wave_dl", children_only=True)
        draw_wave("wave_dl", dpg.get_item_width("wave_dl"), 44)

# ═══════════ UI LAYOUT ═══════════
def build_ui():
    with dpg.window(tag="primary", no_title_bar=True, no_move=True, no_resize=True):
        with dpg.group(horizontal=True):
            # LEFT COLUMN
            with dpg.child_window(width=280, border=True):
                dpg.add_text("SYSTEM CORE", color=C["dim"])
                dpg.add_separator()
                with dpg.drawlist(tag="reactor_dl", width=120, height=120): pass
                dpg.add_text("UPTIME", color=C["dim"])
                dpg.add_text("00:00:00", color=C["cyan"], tag="up_val")
                dpg.add_text("LOCAL CLOCK", color=C["dim"])
                dpg.add_text("00:00:00", color=C["cyan"], tag="clk_val")
                dpg.add_spacer(height=10)
                dpg.add_text("LIVE TELEMETRY", color=C["dim"])
                dpg.add_separator()
                with dpg.drawlist(tag="met_dl", width=250, height=250): pass

            # CENTER COLUMN
            with dpg.child_window(border=True):
                dpg.add_text("COMM CHANNEL // AES-256 ENCRYPTED", color=C["dim"])
                dpg.add_separator()
                with dpg.child_window(tag="chatbox", height=-100, border=False): pass
                dpg.add_text("◈ J.A.R.V.I.S PROCESSING...", color=C["cyan_dim"], tag="busyt", show=False)
                dpg.add_separator()
                with dpg.drawlist(tag="wave_dl", width=600, height=48): pass
                with dpg.group(horizontal=True):
                    dpg.add_text("▶", color=C["cyan_dim"])
                    dpg.add_input_text(tag="inp", hint="// Enter command...", width=-100, on_enter=True, callback=lambda: process_command(None))
                    dpg.add_button(label="SEND", callback=lambda: process_command(None), width=80, height=32)

def main():
    threading.Thread(target=voice_loop, daemon=True).start()
    
    dpg.create_context()
    dpg.create_viewport(title="J.A.R.V.I.S // HUD", width=1000, height=700)
    dpg.setup_dearpygui()
    dpg.bind_theme(make_theme())
    build_ui()
    dpg.show_viewport()
    dpg.set_primary_window("primary", True)
    add_chat_msg("SYS", "ALL PROTOCOLS ACTIVE")
    
    while dpg.is_dearpygui_running():
        loop()
        dpg.render_dearpygui_frame()
    dpg.destroy_context()

if __name__ == "__main__":
    main()

