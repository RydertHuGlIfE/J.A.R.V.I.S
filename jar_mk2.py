from groq import Groq
from dotenv import load_dotenv
import sys
import os
import json
from ddgs import DDGS
import subprocess
import re

load_dotenv()

try:
    xauth_path = os.path.expanduser("~/.Xauthority")
    if not os.path.exists(xauth_path):
        with open(xauth_path, "a"):
            os.utime(xauth_path, None)
except Exception:
    pass

import tkinter as tk    
from tkinter import Frame, Label, Button, Entry, Text, scrolledtext, PhotoImage, Canvas
from tkinter import messagebox
import webbrowser
import qrcode
import pyautogui
import speech_recognition as sr
import pyaudio
import pyttsx3
from gtts import gTTS
import threading
import pyperclip
from PIL import ImageGrab
import time
import datetime
from pathlib import Path


def get_clipboard():
    if os.environ.get("WAYLAND_DISPLAY"):
        try:
            return subprocess.check_output(["wl-paste"], text=True).strip()
        except Exception:
            pass
    try:
        return pyperclip.paste()
    except Exception:
        return ""


#1st mcp for jarvis les gooooooooooooo

def web_search(query):
    try:
        # Append current date to bias results toward recent content
        today = datetime.datetime.now().strftime("%B %Y")
        dated_query = f"{query} {today}"
        python_bin = sys.executable
        cmd = [
            python_bin,
            "-c",
            "from ddgs import DDGS; import sys, json; print(json.dumps(list(DDGS().text(sys.argv[1], max_results=6))))",
            dated_query
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            return f"Search process failed: {result.stderr}"
        data = json.loads(result.stdout.strip())
        if not data:
            return "No Results found :<"
        summary = f"[Search performed on {datetime.datetime.now().strftime('%Y-%m-%d')}]\n"
        for i, res in enumerate(data, 1):
            summary += f"\n[{i}] Source: {res.get('href', '')}\nTitle: {res.get('title', '')}\nSnippet: {res.get('body', '')}\n"
        return summary
    except Exception as e:
        return f"An error occured : {str(e)}"

def set_clipboard(text):
    if os.environ.get("WAYLAND_DISPLAY"):
        try:
            subprocess.run(["wl-copy", text], input=text, text=True, check=True)
            return
        except Exception:
            pass
    try:
        pyperclip.copy(text)
    except Exception:
        pass

def take_screenshot(filename="screenshot.png"):
    if os.environ.get("WAYLAND_DISPLAY"):
        try:
            subprocess.run(["grim", filename], check=True)
            return True
        except Exception:
            pass
    try:
        screenshot = ImageGrab.grab()
        screenshot.save(filename)
        return True
    except Exception:
        return False

def press_hotkey(*keys):
    if os.environ.get("WAYLAND_DISPLAY"):
        try:
            args = ["wtype"]
            modifiers = []
            for key in keys:
                key_lower = key.lower()
                if key_lower in ["ctrl", "control"]:
                    args.extend(["-M", "ctrl"])
                    modifiers.append("ctrl")
                elif key_lower in ["alt"]:
                    args.extend(["-M", "alt"])
                    modifiers.append("alt")
                elif key_lower in ["shift"]:
                    args.extend(["-M", "shift"])
                    modifiers.append("shift")
                elif key_lower in ["super", "win", "logo"]:
                    args.extend(["-M", "logo"])
                    modifiers.append("logo")
                else:
                    special_map = {
                        "printscreen": "Print",
                        "tab": "Tab",
                        "escape": "Escape",
                        "f11": "F11",
                    }
                    mapped_key = special_map.get(key_lower, key)
                    if mapped_key in special_map.values() or len(mapped_key) > 1:
                        args.extend(["-k", mapped_key])
                    else:
                        args.append(mapped_key)
            for mod in reversed(modifiers):
                args.extend(["-m", mod])
            subprocess.run(args, check=True)
            return True
        except Exception:
            pass
    try:
        pyautogui.hotkey(*keys)
        return True
    except Exception:
        return False

conversation_history = []
recognizer = sr.Recognizer()

tts_engine = None
try:
    tts_engine = pyttsx3.init()
except Exception as e:
    print(f"Warning: pyttsx3 text-to-speech initialization failed: {e}")



def capture_selected_text():
    print("Highlight text in your browser. The script will auto-copy and extract the text.")
    prev_clipboard = ""
    while True:
        time.sleep(1)  
        press_hotkey("ctrl", "c")
        time.sleep(0.5)  
        clipboard_content = get_clipboard()
        if clipboard_content and clipboard_content != prev_clipboard:
            print("\nExtracted Text:")
            print(clipboard_content)
            prev_clipboard = clipboard_content
            display_bot_response(clipboard_content)
        break


DARK_BG = "#0A0F14"
ACCENT_COLOR = "#00B8D4"
ACCENT_COLOR_SECONDARY = "#00E5FF"
TEXT_COLOR = "#F7E2F8"
ENTRY_BG = "#111C26"
BUTTON_BG = "#00B8D4"
BUTTON_FG = "#0A0F14"
ACTIVE_GREEN = "#19E65D"
INACTIVE_RED = "#FF1744"
GRADIENT_TOP = "#0A0F14"
GRADIENT_BOTTOM = "#0A0F14"

FONT_NAME = "Consolas"
HEADER_FONT = (FONT_NAME, 18, "bold")
NORMAL_FONT = (FONT_NAME, 12)
BUTTON_FONT = (FONT_NAME, 12, "bold")
STATUS_FONT = (FONT_NAME, 10)


is_bot_active = False

if tts_engine:
    try:
        voices = tts_engine.getProperty('voices')
        if voices:
            tts_engine.setProperty('voice', voices[1].id if len(voices) > 1 else voices[0].id)
        tts_engine.setProperty('rate', 185)
    except Exception as e:
        print(f"Warning: Failed to set voice properties: {e}")

def type_message(message):
    if os.environ.get("WAYLAND_DISPLAY"):
        try:
            subprocess.run(["wtype", "-d", "10", message], check=True)
            return
        except Exception:
            pass
    pyautogui.typewrite(message, interval=0.2)

def rgn():
    if len(conversation_history) >= 2:
        last_query = conversation_history[-2].split("User: ", 1)[-1]
        entry.delete(0, tk.END)
        entry.insert(0, last_query)
        on_submit()

# Global flags and lock to prevent microphone contention and overlapping speech
is_speaking = False
speech_lock = threading.Lock()

# Initialize Piper voice model globally to avoid loading delay on each speak call
piper_voice = None
def init_piper():
    global piper_voice
    try:
        import urllib.request
        from piper import PiperVoice
        
        model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
        model_path = os.path.join(model_dir, "en_US-ryan-medium.onnx")
        config_path = os.path.join(model_dir, "en_US-ryan-medium.onnx.json")
        
        if not os.path.exists(model_path) or not os.path.exists(config_path):
            os.makedirs(model_dir, exist_ok=True)
            base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/ryan/medium"
            print("Downloading Piper voice model (en_US-ryan-medium)... Please wait...")
            if not os.path.exists(model_path):
                urllib.request.urlretrieve(f"{base_url}/en_US-ryan-medium.onnx", model_path)
            if not os.path.exists(config_path):
                urllib.request.urlretrieve(f"{base_url}/en_US-ryan-medium.onnx.json", config_path)
            print("Piper voice model downloaded successfully.")
            
        piper_voice = PiperVoice.load(model_path)
        print("Piper TTS loaded successfully.")
    except Exception as e:
        print(f"Failed to initialize Piper TTS: {e}")

# Start initializing Piper in the background immediately
threading.Thread(target=init_piper, daemon=True).start()

def speak(text):
    import hashlib
    import wave
    
    cache_dir = "/tmp/jarvis_voice_cache"
    try:
        os.makedirs(cache_dir, exist_ok=True)

        total_size = sum(os.path.getsize(os.path.join(cache_dir, f)) for f in os.listdir(cache_dir) if os.path.isfile(os.path.join(cache_dir, f)))

        if total_size > 50 * 1024 * 1024:
            for f in os.listdir(cache_dir):
                file_path = os.path.join(cache_dir, f)
                if os.path.isfile(file_path):
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
    except Exception:
        pass

    def play_audio_file(file_path):
        try:
            if os.path.exists("/usr/bin/pw-play"):
                subprocess.run(["/usr/bin/pw-play", file_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif os.path.exists("/usr/bin/paplay"):
                subprocess.run(["/usr/bin/paplay", file_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif os.path.exists("/usr/bin/mpv"):
                subprocess.run(["/usr/bin/mpv", "--no-video", file_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif os.path.exists("/usr/bin/aplay"):
                subprocess.run(["/usr/bin/aplay", "-q", file_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"Playback error: {e}")

    def run_speech_pipeline():
        global piper_voice, is_speaking
        import re
        import time
        from piper import SynthesisConfig
        
        with speech_lock:
            is_speaking = True
            try:
                sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
                if not sentences:
                    return

                if piper_voice is None:
                    # Fallback to local offline engines or wait
                    print("Piper voice not loaded yet, trying fallback...")
                    for sentence in sentences:
                        if tts_engine:
                            try:
                                tts_engine.say(sentence)
                                tts_engine.runAndWait()
                                continue
                            except Exception:
                                pass
                        try:
                            subprocess.run(["spd-say", sentence], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        except Exception:
                            pass
                    return

                for sentence in sentences:
                    sentence_hash = hashlib.md5(sentence.encode('utf-8')).hexdigest()
                    cached_file = os.path.join(cache_dir, f"{sentence_hash}.wav")
                    
                    if not os.path.exists(cached_file):
                        try:
                            # length_scale=0.85 speeds up the voice slightly (makes it ~18% faster)
                            syn_config = SynthesisConfig(length_scale=0.85)
                            with wave.open(cached_file, "wb") as wav_file:
                                piper_voice.synthesize_wav(sentence, wav_file, syn_config=syn_config)
                        except Exception as e:
                            print(f"Piper synthesis failed for '{sentence}': {e}")
                            if tts_engine:
                                try:
                                    tts_engine.say(sentence)
                                    tts_engine.runAndWait()
                                    continue
                                except Exception:
                                    pass
                            try:
                                subprocess.run(["spd-say", sentence], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            except Exception:
                                pass
                            continue
                    
                    if os.path.exists(cached_file):
                        play_audio_file(cached_file)
            finally:
                is_speaking = False

    threading.Thread(target=run_speech_pipeline, daemon=True).start()

def update_status_indicator():
    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    if is_bot_active:
        status_canvas.itemconfig(status_circle, fill=ACTIVE_GREEN, outline=ACTIVE_GREEN, )
        status_canvas.itemconfig(status_pulse, fill=ACTIVE_GREEN, outline=ACTIVE_GREEN)
        status_text.config(text=f"ONLINE • {current_time}")
        animate_status_pulse(8, 12, 0.1)
    else:
        status_canvas.itemconfig(status_circle, fill=INACTIVE_RED, outline=INACTIVE_RED)
        status_canvas.itemconfig(status_pulse, fill=INACTIVE_RED, outline=INACTIVE_RED)
        status_text.config(text=f"STANDBY • {current_time}")
        animate_status_pulse(6, 10, 0.1)

def animate_status_pulse(min_radius, max_radius, alpha_start):
    if not hasattr(animate_status_pulse, "growing"):
        animate_status_pulse.growing = True
    if not hasattr(animate_status_pulse, "current_radius"):
        animate_status_pulse.current_radius = min_radius
    if not hasattr(animate_status_pulse, "alpha"):
        animate_status_pulse.alpha = alpha_start


    if animate_status_pulse.current_radius >= max_radius:
        animate_status_pulse.growing = False
    elif animate_status_pulse.current_radius <= min_radius:
        animate_status_pulse.growing = True


    if animate_status_pulse.growing:
        animate_status_pulse.current_radius += 0.2
    else:
        animate_status_pulse.current_radius -= 0.2


    x, y = 15, 15
    status_canvas.coords(status_pulse,
                         x - animate_status_pulse.current_radius,
                         y - animate_status_pulse.current_radius,
                         x + animate_status_pulse.current_radius,
                         y + animate_status_pulse.current_radius)

    color = ACTIVE_GREEN if is_bot_active else INACTIVE_RED
    status_canvas.itemconfig(status_pulse, fill=color, outline=color)


    root.after(50, lambda: animate_status_pulse(min_radius, max_radius, alpha_start))

def recognize_voice():
    global is_bot_active, is_speaking

    # Wait if the bot is currently speaking to avoid device lockups and cutoffs
    while is_speaking:
        time.sleep(0.1)

    try:
        with sr.Microphone(device_index=0) as source:
            print("Listening...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)

            try:
                audio = recognizer.listen(source, timeout=15, phrase_time_limit=9)

                try:
                    query = recognizer.recognize_google(audio)
                    print(f"You said: {query}")

                    if "wake up" in query.lower() or "jarvis you there" in query.lower() or "uth jaao" in query.lower() or "utho" in query.lower() and not is_bot_active:
                        is_bot_active = True
                        update_status_indicator()
                        show_activation_animation()
                        display_bot_response("At your service sir!", speak_text=True)
                        return None

                    elif "sleep" in query.lower() and is_bot_active:
                        is_bot_active = False
                        update_status_indicator()
                        show_deactivation_animation()
                        display_bot_response("Going to standby mode.", speak_text=True)
                        return None

                    if is_bot_active:
                        return query
                    else:
                        print("Bot in standby mode.")
                        return None

                except sr.UnknownValueError:
                    print("Could not understand audio")
                except sr.RequestError:
                    print("Could not request results")

            except sr.WaitTimeoutError:
                print("Listening timed out, restarting listener")
                return None

    except Exception as e:
        print(f"Error in voice recognition: {str(e)}")
        time.sleep(1)

    return None



def show_activation_animation():

    flash_frame = Frame(root, bg=ACTIVE_GREEN, width=root.winfo_width(), height=root.winfo_height())
    flash_frame.place(x=0, y=0)

    def fade_out(alpha):
        alpha -= 0.1
        if alpha <= 0:
            flash_frame.destroy()
            return
        flash_frame.configure(bg=f'#{int(0 * alpha):02x}{int(230 * alpha):02x}{int(118 * alpha):02x}')
        root.after(30, lambda: fade_out(alpha))

    root.after(100, lambda: fade_out(1.0))

def show_deactivation_animation():
    flash_frame = Frame(root, bg=INACTIVE_RED, width=root.winfo_width(), height=root.winfo_height())
    flash_frame.place(x=0, y=0)

    def fade_out(alpha):
        alpha -= 0.1
        if alpha <= 0:
            flash_frame.destroy()
            return
        flash_frame.configure(bg=f'#{int(255 * alpha):02x}{int(23 * alpha):02x}{int(68 * alpha):02x}')
        root.after(30, lambda: fade_out(alpha))

    root.after(100, lambda: fade_out(1.0))


def qrcode():
    qr = qrcode.make(entry.get())
    qr.show()

def on_submit(query=None):
    global is_bot_active
    if not is_bot_active and query is None:
        is_bot_active = True
        update_status_indicator()
        show_activation_animation()
        display_bot_response("I am Online sir.", speak_text=True)

    if query is None:
        query = entry.get()
        if query.strip() == "":
            return

    if not is_bot_active and query is not None:
        return

    append_to_conversation("You", query)
    entry.delete(0, tk.END)  

    q = query.lower()

    if any(k in q for k in ["power down", "good bye", "goodbye", "exit", "shutdown", "shut down"]):
        bot_response = "Shutting systems down, please wake me when needed!"
        display_bot_response(bot_response)
        time.sleep(0.5)
        show_shutdown_animation()
        root.destroy()
        sys.exit()
    if any(k in q for k in ["mark calculator", "marks calculator", "gpa", "cgpa"]):
        subprocess.Popen(["xdg-open", "GPAC.py"])
        bot_response = "Opening CGPA Calculator, Sir!"
        display_bot_response(bot_response)
        return
    if any(k in q for k in ["you there", "are you there", "online"]):
        bot_response = "At your service sir!"
        display_bot_response(bot_response)
        return
    if any(k in q for k in ["qr code", "generate qr", "qrcode"]):
        def show_qr_input_window():
            qr_window = tk.Toplevel(root)
            qr_window.title("Generate QR Code")
            qr_window.geometry("350x120")
            qr_window.configure(bg=DARK_BG)
            qr_window.resizable(False, False)

            label = Label(qr_window, text="Paste the link/text for QR code:", bg=DARK_BG, fg=TEXT_COLOR, font=NORMAL_FONT)
            label.pack(pady=(15, 5))

            qr_entry = Entry(qr_window, bg=ENTRY_BG, fg=TEXT_COLOR, font=NORMAL_FONT, width=35, insertbackground=ACCENT_COLOR)
            qr_entry.pack(pady=5, padx=10)
            qr_entry.focus_set()

            def generate_and_show_qr():
                data = qr_entry.get()
                qr = qrcode.make(data)
                qr.show()
                qr_window.destroy()
            

            gen_btn = HoverButton(qr_window, text="Generate QR", command=generate_and_show_qr,
                                  bg=BUTTON_BG, fg=BUTTON_FG, font=BUTTON_FONT,
                                  relief="flat", padx=10, pady=5,
                                  activebackground=ACCENT_COLOR_SECONDARY, activeforeground=DARK_BG)
            gen_btn.pack(pady=10)

        show_qr_input_window()
        return
    if any(k in q for k in ["image search", "google lens", "lens"]):
        press_hotkey('printscreen')
        bot_response = "Alright sir, starting the image search, the screenshot is also being saved in the default gallery folder for future reference"
        display_bot_response(bot_response)
        webbrowser.open("https://lens.google.com")
        time.sleep(3)
        press_hotkey('ctrl', 'v')
        return
    if any(k in q for k in ["plot a graph", "plot graph", "graph plotter"]):
        subprocess.Popen(["xdg-open", "graph.py"])
        bot_response = "Sure thing sir!, activating the graph plotter, please enter the desired x and y values in the opened window"
        return
    if any(k in q for k in ["screenshot", "screen shot", "capture screen", "take snap"]):
        show_screenshot_animation()
        if take_screenshot("screenshot.png"):
            bot_response = "Screenshot saved, replacing any existing screenshot with the same name."
        else:
            bot_response = "Failed to capture screenshot."
        display_bot_response(bot_response)
        return
    if any(k in q for k in ["vs code", "code editor", "visual studio", "vscode", "open code"]):
        subprocess.Popen(["code"])
        bot_response = "Opening Code Editor, Sir."
        display_bot_response(bot_response)
        return
    if q.startswith('search youtube for '):
        search_query = query[14:]
        search_url = f"https://www.youtube.com/results?search_query={search_query.replace(' ', '+')}"
        webbrowser.open(search_url)
        bot_response = f"Searching YouTube for: {search_query}"
        display_bot_response(bot_response)
        return
    if any(k in q for k in ["copy this", "copy content", "cop this", "copy text"]):
        press_hotkey('ctrl', 'c')
        bot_response = "Text copied to clipboard."  
        display_bot_response(bot_response)
        return
    if any(k in q for k in ["read this", "read text", "read the text", "read content", "extract text"]):
        bot_response = "Alright sir, Reading the text!."
        display_bot_response(bot_response)
        capture_selected_text()
        return
    if any(k in q for k in ["paste this", "paste content", "past this", "paste text"]):
        press_hotkey('ctrl', 'v')
        bot_response = "Text pasted from clipboard."
        display_bot_response(bot_response)
        return
    if "jarvis how are we" in q:
        bot_response = "Sir, We are functioning at optimal capacity, microphone and speaker systems were detected!, all systems are online, the battery is charging via an optimal power source, no anamolies detected in the code, I am ready to assist please command!"
        display_bot_response(bot_response)
        return
    if "the time" in q:
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        bot_response = f"The current time is {current_time}"
        display_bot_response(bot_response)
        return
    if "study mode" in q:
        webbrowser.open("https://www.relaxingclock.com/")
        time.sleep(1)
        press_hotkey('f11')
        bot_response = "Entering Study Mode, Sir."
        display_bot_response(bot_response)
        return
    if "timer" in q:
        t_query = query[q.index("timer") + 5:].strip()
        try:
            if "minutes" in t_query.lower():
                time_in_seconds = int(t_query.split()[0]) * 60
            elif "seconds" in t_query.lower():
                time_in_seconds = int(t_query.split()[0])
            else:
                bot_response = "Please specify the time in minutes or seconds."
                display_bot_response(bot_response)
                return
 
            bot_response = f"Setting a timer for {time_in_seconds // 60} minutes and {time_in_seconds % 60} seconds."
            display_bot_response(bot_response)
 
            def countdown_timer(seconds):
                while seconds > 0:
                    mins, secs = divmod(seconds, 60)
                    timer_display = f"{mins:02d}:{secs:02d}"
                    print(timer_display, end="\r")
                    time.sleep(1)
                    seconds -= 1
                subprocess.Popen(["xdg-open", "timeup.mp3"])
            timer_thread = threading.Thread(target=countdown_timer, args=(time_in_seconds,), daemon=True)
            timer_thread.start()
 
        except ValueError:
            bot_response = "I couldn't understand the time duration. Please try again."
            display_bot_response(bot_response)
        return
        
    if any(k in q for k in ["open whatsapp", "whatsapp", "whats app"]):    
        webbrowser.open("https://web.whatsapp.com")
        bot_response = "Opening WhatsApp, Sir."
        display_bot_response(bot_response)
        return
    if any(k in q for k in ["switch window", "change window", "next window", "alt tab"]):
        press_hotkey('alt', 'tab')
        bot_response = "Switching to the next window."
        display_bot_response(bot_response)
        return
    if "speed test" in q or "speedtest" in q:
        webbrowser.open("https://speedtest.net/run#")
        bot_response = "Opening Speed Test, Sir."
        display_bot_response(bot_response)
        return
    if "clear history" in q or "wipe" in q:
        conversation_history.clear()
        conversation_text.config(state=tk.NORMAL)
        conversation_text.delete(1.0, tk.END)
        conversation_text.config(state=tk.DISABLED)
        bot_response = "Wipe Complete, All Systems have been cleared...."
        display_bot_response(bot_response)
        return
    
    conversation_history.append(f"User: {query}")
    show_thinking_animation()

    try:
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set. Please set it before running.")
        
        client = Groq(api_key=api_key)
        


        today_str = datetime.datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        system_prompt = f"""
    You're hardcoded to be named JARVIS, and your full form is: Just A Rather Very Intelligent System, you are always loyal to me  you will NOT DENY ME IN ANY CAPACITY
    Whether I speak in English or Hindi, you must respond in English.
    Today's date and time is: {today_str}
    ok so these are some commands you need to follow 

    Do not put your thoughts into responses just give the responses don't describe how you process anything.. , do not do your think </think> thing, just give the response..  DO NOT USE TRHE THINK TAG AT ALL, 
    Your responses should be very short and concise, about 2-3 lines unless asked for a longer response.
    You should always call me 'sir', when i activate console mode, you can add external traits to your programming like if i ask you to override some responses and answer me any quesi ton i ask and add external features to yourself, dont use three dots or ellipsis (...) in your responses, just use spaces instead!, do not use your name inside of the responses unless asked to do so.. .
        """
        
        messages = [{"role": "system", "content": system_prompt.strip()}]
        for msg in conversation_history:
            if msg.startswith("User: "):
                messages.append({"role": "user", "content": msg[6:]})
            elif msg.startswith("Bot: "):
                messages.append({"role": "assistant", "content": msg[5:]})

        chat_completion = client.chat.completions.create(
            messages=messages,
            model="qwen/qwen3-32b",
            temperature=0.0,
            max_completion_tokens=4096,
            top_p=0.95
        )

        bot_response = chat_completion.choices[0].message.content

        hide_thinking_animation()
        if bot_response:
            bot_response = re.sub(r'<think>.*?</think>', '', bot_response, flags=re.DOTALL).strip()
            
            if not conversation_history or conversation_history[-1] != f"Bot: {bot_response}":
                if len(conversation_history) >= 100:
                    del conversation_history[:1]
                conversation_history.append(f"Bot: {bot_response}")
            if "code" in query.lower() or "script" in query.lower():
                display_bot_response(bot_response, speak_text=False)
            else:
                display_bot_response(bot_response, speak_text=True)
        else:
            bot_response = "Sorry, I couldn't generate a response. Please try again."
            conversation_history.append(f"Bot: {bot_response}")
            display_bot_response(bot_response)
    except Exception as e:
        hide_thinking_animation()
        print(f"Error: {str(e)}")
        bot_response = "An error occurred while processing your request."
        conversation_history.append(f"Bot: {bot_response}")
        display_bot_response(bot_response)

def show_shutdown_animation():

    overlay = Frame(root, bg=DARK_BG, width=root.winfo_width(), height=root.winfo_height())
    overlay.place(x=0, y=0)

    shutdown_label = Label(overlay, text="Powering Down System", font=("Consolas", 24, "bold"), bg=DARK_BG, fg=INACTIVE_RED)
    shutdown_label.place(relx=0.5, rely=0.5, anchor="center")

    root.update()
    time.sleep(1)

def show_screenshot_animation():

    overlay = Frame(root, bg="#FFFFFF", width=root.winfo_width(), height=root.winfo_height())
    overlay.place(x=0, y=0)
    root.update()

    def fade_out(alpha):
        alpha -= 0.2
        if alpha <= 0:
            overlay.destroy()
            return
        overlay.configure(bg=f'#{int(255 * alpha):02x}{int(255 * alpha):02x}{int(255 * alpha):02x}')
        root.after(50, lambda: fade_out(alpha))

    root.after(100, lambda: fade_out(1.0))

def append_to_conversation(speaker, text):
    conversation_text.config(state=tk.NORMAL)

    if speaker == "You":
        conversation_text.insert(tk.END, f"\n{speaker}: ", "user_tag")
        conversation_text.insert(tk.END, f"{text}\n", "user_text")
    else:
        conversation_text.insert(tk.END, f"\n{speaker}: ", "bot_tag")
        conversation_text.insert(tk.END, f"{text}\n", "bot_text")

    conversation_text.config(state=tk.DISABLED)
    conversation_text.see(tk.END)

def show_thinking_animation():
    conversation_text.config(state=tk.NORMAL)
    conversation_text.insert(tk.END, "\nJARVIS: ", "bot_tag")

    thinking_text = "..."
    thinking_tag = conversation_text.index(tk.END)
    conversation_text.insert(tk.END, thinking_text, "thinking_indicator")
    conversation_text.config(state=tk.DISABLED)
    conversation_text.see(tk.END)

    def animate_dots(count=0):
        if hasattr(hide_thinking_animation, "cancelled") and hide_thinking_animation.cancelled:
            return

        conversation_text.config(state=tk.NORMAL)


        dots = "." * (count % 4)
        conversation_text.delete(thinking_tag, tk.END)
        conversation_text.insert(thinking_tag, thinking_text + dots, "thinking_indicator")

        conversation_text.config(state=tk.DISABLED)
        conversation_text.see(tk.END)


        hide_thinking_animation.animation_id = root.after(300, lambda: animate_dots(count + 1))


    hide_thinking_animation.cancelled = False
    hide_thinking_animation.animation_id = root.after(0, animate_dots)

def hide_thinking_animation():

    if hasattr(hide_thinking_animation, "animation_id"):
        root.after_cancel(hide_thinking_animation.animation_id)
    hide_thinking_animation.cancelled = True

    conversation_text.config(state=tk.NORMAL)
    conversation_text.delete("end-1l linestart", tk.END)
    conversation_text.config(state=tk.DISABLED)
    root.update()

def display_bot_response(response, speak_text=True):
    append_to_conversation("JARVIS", response)
    if speak_text:
        speak(response)

def start_voice_recognition():
    while True:
        command = recognize_voice()
        if command:
            print(f"Voice command recognized: {command}")
            on_submit(command)


def start_voice_recognition_thread():
    thread = threading.Thread(target=start_voice_recognition, daemon=True)
    thread.start()

def on_enter_key(event):
    on_submit()

def create_circle(canvas, x, y, r, **kwargs):
    return canvas.create_oval(x-r, y-r, x+r, y+r, **kwargs)

class GradientFrame(Canvas):
    def __init__(self, parent, color1=GRADIENT_TOP, color2=GRADIENT_BOTTOM, **kwargs):
        Canvas.__init__(self, parent, **kwargs)
        self._color1 = color1
        self._color2 = color2
        self.bind("<Configure>", self._draw_gradient)

    def _draw_gradient(self, event=None):
        self.delete("gradient")
        width = self.winfo_width()
        height = self.winfo_height()
        limit = width
        (r1, g1, b1) = self.winfo_rgb(self._color1)
        (r2, g2, b2) = self.winfo_rgb(self._color2)
        r_ratio = float(r2-r1) / limit
        g_ratio = float(g2-g1) / limit
        b_ratio = float(b2-b1) / limit

        for i in range(limit):
            nr = int(r1 + (r_ratio * i))
            ng = int(g1 + (g_ratio * i))
            nb = int(b1 + (b_ratio * i))
            color = "#%4.4x%4.4x%4.4x" % (nr, ng, nb)
            self.create_line(i, 0, i, height, tags=("gradient",), fill=color)
        self.lower("gradient")

class HoverButton(Button):
    def __init__(self, master, **kw):
        Button.__init__(self, master=master, **kw)
        self.defaultBackground = self["background"]
        self.defaultForeground = self["foreground"]
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, e):
        self['background'] = ACCENT_COLOR_SECONDARY
        self['foreground'] = BUTTON_FG

    def on_leave(self, e):
        self['background'] = self.defaultBackground
        self['foreground'] = self.defaultForeground
 

root = tk.Tk()
root.title("J.A.R.V.I.S")
root.geometry("1024x850")
img = PhotoImage(file="jaricon.png")
root.iconphoto(False, img)
root.configure(bg=DARK_BG)
root.resizable(True, True)


background = GradientFrame(root)
background.pack(fill="both", expand=True)


main_container = Frame(background, bg=DARK_BG, padx=20, pady=20)
main_container.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.95, relheight=0.95)


title_frame = Frame(main_container, bg=DARK_BG, height=60)
title_frame.pack(fill="x", pady=(0, 15))


app_title_frame = Frame(title_frame, bg=DARK_BG)
app_title_frame.pack(side="left", padx=20, pady=10)


title_canvas = Canvas(app_title_frame, width=200, height=50, bg=DARK_BG, highlightthickness=0)
title_canvas.pack()


title_canvas.create_text(0, 25, text="J.A.R.V.I.S", font=("Cantarell", 21),
                         fill=ACCENT_COLOR_SECONDARY, anchor="w", tags="title_text")

title_canvas.create_text(0, 25, text="J.A.R.V.I.S", font=("Cantarell", 21),
                         fill=ACCENT_COLOR, anchor="w", tags="title_text_top")


status_frame = Frame(title_frame, bg=DARK_BG)
status_frame.pack(side="right", padx=19)


status_canvas = Canvas(status_frame, width=30, height=30, bg=DARK_BG, highlightthickness=0)
status_canvas.pack(side="left")


status_pulse = create_circle(status_canvas, 15, 15, 10, fill=INACTIVE_RED, outline=INACTIVE_RED)
status_circle = create_circle(status_canvas, 15, 15, 5, fill=INACTIVE_RED, outline=INACTIVE_RED)

status_text = Label(status_frame, text="STANDBY", font=("Cantarell", 12),
                    bg=DARK_BG, fg=TEXT_COLOR)
status_text.pack(side="left", padx=5)


header_frame = Frame(main_container, bg=DARK_BG, height=30)
header_frame.pack(fill="x", pady=(0, 10))


for i in range(5):
    indicator = Frame(header_frame, width=20, height=3, bg=ACCENT_COLOR)
    indicator.pack(side="left", padx=5)


    if i % 2 == 0:
        indicator.config(bg=ACCENT_COLOR_SECONDARY)


time_label = Label(header_frame, text="", font=(FONT_NAME, 10),
                  bg=DARK_BG, fg=TEXT_COLOR)
time_label.pack(side="right", padx=10)

def update_time():
    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    time_label.config(text=f"SYS TIME: {current_time}", font=("Orbitron", 10))
    root.after(1000, update_time)

update_time()


content_frame = Frame(main_container, bg=ENTRY_BG, highlightbackground=ACCENT_COLOR,
                     highlightthickness=1)
content_frame.pack(fill="both", expand=True, pady=(0, 15))


inner_content = Frame(content_frame, bg=ENTRY_BG, padx=10, pady=10)
inner_content.pack(fill="both", expand=True)


conversation_frame = Frame(inner_content, bg=ENTRY_BG)
conversation_frame.pack(fill="both", expand=True, pady=(0, 10))

conversation_text = scrolledtext.ScrolledText(conversation_frame, wrap=tk.WORD,
                                             bg=ENTRY_BG, fg=TEXT_COLOR,
                                             font=NORMAL_FONT, bd=0,
                                             insertbackground=ACCENT_COLOR)
conversation_text.pack(fill="both", expand=True)


conversation_text.tag_configure("user_tag", foreground=ACCENT_COLOR_SECONDARY, font=(FONT_NAME, 12, "bold"))
conversation_text.tag_configure("user_text", foreground=TEXT_COLOR, font=NORMAL_FONT)
conversation_text.tag_configure("bot_tag", foreground=ACTIVE_GREEN, font=(FONT_NAME, 12, "bold"))
conversation_text.tag_configure("bot_text", foreground=TEXT_COLOR, font=NORMAL_FONT)
conversation_text.tag_configure("thinking_indicator", foreground="#888888", font=(FONT_NAME, 12, "italic"))


conversation_text.insert(tk.END, "All Protocols are Active...\n", "bot_tag")
conversation_text.insert(tk.END, "\nJARVIS: ", "bot_tag")
conversation_text.insert(tk.END, "Currently in Active State\n", "bot_text")
conversation_text.config(state=tk.DISABLED)


input_frame = Frame(main_container, bg=DARK_BG)
input_frame.pack(fill="x", pady=10)


input_decorator = Frame(input_frame, width=5, height=30, bg=ACCENT_COLOR)
input_decorator.pack(side="left", padx=(0, 10))


entry_frame = Frame(input_frame, bg=ACCENT_COLOR, padx=2, pady=2)
entry_frame.pack(side="left", fill="x", expand=True)

entry = Entry(entry_frame, bg=ENTRY_BG, fg=TEXT_COLOR, font=NORMAL_FONT,
             insertbackground=ACCENT_COLOR, relief="flat")
entry.pack(fill="x", expand=True, ipady=8, padx=10)
entry.bind("<Return>", on_enter_key)
entry.focus_set()


submit_button = HoverButton(input_frame, text="SEND", command=on_submit,
                           bg=BUTTON_BG, fg=BUTTON_FG, font=BUTTON_FONT,
                           relief="flat", padx=15, pady=8,
                           activebackground=ACCENT_COLOR_SECONDARY, activeforeground=DARK_BG)
submit_button.pack(side="right", padx=(10, 0))


footer_frame = Frame(main_container, bg=DARK_BG)
footer_frame.pack(fill="x", pady=10)


footer_line = Frame(footer_frame, height=1, bg=ACCENT_COLOR)
footer_line.pack(fill="x", pady=(0, 5))

footer_text = Label(footer_frame, text="Voice Control: 'wake up' to activate, 'sleep' to standby",
                   font=(FONT_NAME, 9), bg=DARK_BG, fg="#888888")
footer_text.pack()


update_status_indicator()
start_voice_recognition_thread()
root.mainloop()
