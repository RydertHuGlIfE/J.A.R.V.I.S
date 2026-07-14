from groq import Groq
from dotenv import load_dotenv
import sys
import os
import json
import subprocess
import re

load_dotenv()


# Create global Groq client to enable TCP connection pooling and Keep-Alive
api_key = os.environ.get("GROQ_API_KEY", "")
if not api_key:
    print("Warning: GROQ_API_KEY is not set in the environment.")
client = Groq(api_key=api_key)

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
from datetime import datetime



#code for supression of HOLY SO MANY LINUX MIC BS WARNINGS WHEN DEF_MIC_STATE == 0, FFS 
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


def_mic_state = 0

HISTORY_LOG = "history.json"


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


#step1 to control pc 

def execute_terminal_command(command):
    import subprocess
    try:
        # Use Popen so we don't automatically kill the process on timeout
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        try:
            # Wait 15.0 seconds for search/web/python commands, and 1.8 seconds for others
            timeout_val = 1.8
            if any(x in command for x in ["curl", "wget", "python"]):
                timeout_val = 15.0
            output, error = process.communicate(timeout=timeout_val)
        except subprocess.TimeoutExpired:
            # If it's a CLI tool, terminate it and return a timeout error
            if not command.strip().startswith("kitty") and any(x in command for x in ["curl", "wget", "python"]):
                process.terminate()
                try:
                    process.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                return f"Error: Command '{command}' timed out after {timeout_val} seconds."
            else:
                # Let GUI apps (like Kitty) keep running in the background!
                return f"Command '{command}' launched successfully and is running in the background."
            
        output = output.strip()
        error = error.strip()

        response = ""
        if output:
            response += f"Output:\n{output}\n"
        if error:
            response += f"Error:\n{error}\n"
            
        if not response:
            return "Command executed successfully with no output."
            
        return response
        
    except Exception as e:
        return f"Failed to execute Python subprocess: {str(e)}"

def scan_directory(path):
    import os
    if not os.path.exists(path):
        return f"Error: Path '{path}' does not exist."
    if not os.path.isdir(path):
        return f"Error: Path '{path}' is not a directory."
        
    ignore_dirs = {'.git', 'venv', '__pycache__', 'node_modules', '.idea', '.vscode', '.lapce', '.ropeproject'}
    ignore_files = {'.DS_Store', 'thumbs.db'}
    
    result = []
    for root_dir, dirs, files in os.walk(path):
        # Exclude ignored directories in-place so walk doesn't visit them
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        rel_path = os.path.relpath(root_dir, path)
        if rel_path == '.':
            level = 0
            result.append(f"Directory Structure for: {path}\n")
        else:
            level = rel_path.count(os.sep) + 1
            indent = "  " * level
            result.append(f"{indent}📁 {os.path.basename(root_dir)}/\n")
            
        indent_files = "  " * (level + 1)
        for f in files:
            if f not in ignore_files:
                result.append(f"{indent_files}📄 {f}\n")
                
    output = "".join(result)
    # Truncate to keep context window safe
    if len(output) > 2500:
        return output[:2500] + "\n...[TRUNCATED due to size limit]..."
    return output

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
script_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.environ.get("LOG_FILE", os.path.join(script_dir, "history.log"))
last_70b_rate_limit_time = 0.0
recognizer = sr.Recognizer()

def create_chat_completion_with_fallback(messages, tools=None, tool_choice=None, timeout=15.0):
    global last_70b_rate_limit_time
    cooldown = 300.0
    now = time.time()
    
    candidates = []
    if (now - last_70b_rate_limit_time) >= cooldown:
        candidates.append("llama-3.3-70b-versatile")
    candidates.append("llama-3.1-8b-instant")

    success_event = threading.Event()
    results = {}
    errors = {}
    lock = threading.Lock()
    
    def query_single_model(model_name):
        try:
            params = {
                "model": model_name, 
                "messages": messages,
                "temperature": 0.0, 
                "max_completion_tokens": 1024,
                "top_p": 0.95,
                "timeout": timeout
            }

            if tools:
                params["tools"] = tools
                params["tool_choice"] = tool_choice
            
            completion = client.chat.completions.create(**params)
            
            with lock:
                #save winning thread
                if not success_event.is_set():
                    results["winner"] = completion
                    results["model"] = model_name
                    print(f"{model_name} won")
                    success_event.set()
        except Exception as e:
            with lock:
                errors[model_name] = str(e)
            print(f"{model_name} failed: {e}")
            global last_70b_rate_limit_time
            last_70b_rate_limit_time = time.time()


        threads = []
        for model_name in candidates:
            thread = threading.Thread(target=query_single_model, args=(model_name,), daemon=True)
            thread.start()
            threads.append(thread)


        for thread in threads:
            thread.join(timeout=timeout+2.0)


        if "winner" in results:
            print(f"JARVIS: {results['winner']}")
            return results["winner"]



        raise Exception(f"All Parallel LLM Operations FAILED {errors}")

        


            


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


# ═══════════════════════════════════════════════════════════════════
# ██  J.A.R.V.I.S  HUD  DESIGN  SYSTEM  v2.0  ██
# ═══════════════════════════════════════════════════════════════════

# ── Core Palette ──
DARK_BG = "#050505"                    # Void Black
GLASS_BG = "#0D0D0D"                   # 20% charcoal glass layer
GLASS_PANEL = "#111111"                # Panel interior
ACCENT_COLOR = "#00E5FF"               # Glowing Cyan (Primary)
ACCENT_COLOR_SECONDARY = "#FFB300"     # Arc Gold (Secondary)
TEXT_COLOR = "#E0F7FA"                 # Light cyan-tinted white
TEXT_DIM = "#4A6572"                   # Dimmed structural text
ENTRY_BG = "#0A0E12"                   # Deep input field bg
BUTTON_BG = "#00E5FF"                  # Cyan button
BUTTON_FG = "#050505"                  # Dark text on buttons
ACTIVE_GREEN = "#00E676"               # System online
INACTIVE_RED = "#FF003C"               # Danger / Critical Red
GRADIENT_TOP = "#050505"               # Gradient start
GRADIENT_BOTTOM = "#0A1520"            # Gradient end (subtle blue)
RING_CYAN = "#00E5FF"                  # Concentric ring color 1
RING_GOLD = "#FFB300"                  # Concentric ring color 2
HEX_GRID_COLOR = "#00E5FF"             # Hex overlay stroke
GLOW_CYAN_SOFT = "#004D5A"             # Subtle cyan glow for borders
GLOW_GOLD_SOFT = "#5A3D00"             # Subtle gold glow for borders
SEPARATOR_COLOR = "#0D3B47"            # Divider lines

# ── Typography ──
FONT_DISPLAY = "Orbitron"              # Geometric sans-serif (titles)
FONT_MONO = "JetBrains Mono"           # Monospaced (data readouts)
FONT_FALLBACK = "Consolas"             # Fallback monospace
FONT_NAME = FONT_MONO                  # Default body font
HEADER_FONT = (FONT_DISPLAY, 18, "bold")
NORMAL_FONT = (FONT_MONO, 11)
BUTTON_FONT = (FONT_DISPLAY, 11, "bold")
STATUS_FONT = (FONT_MONO, 9)
DATA_FONT = (FONT_MONO, 10)            # For HUD data readouts
TITLE_FONT = (FONT_DISPLAY, 24, "bold")

# ── HUD Animation Config ──
HUD_RING_COUNT = 4                     # Number of concentric rings
HUD_RING_BASE_RADIUS = 40              # Smallest ring radius
HUD_RING_GAP = 18                      # Gap between rings
HUD_RING_SPEED_BASE = 0.8              # Degrees per frame (base)
HEX_GRID_SIZE = 22                     # Hex cell size in pixels
WAVEFORM_BARS = 32                     # Number of waveform bars
WAVEFORM_MAX_HEIGHT = 40               # Max bar height
import math
import random


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
    import re
    
    # If the response is longer than 5 sentences, summarize it verbally
    s_check = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    if len(s_check) > 5:
        text = "Message too long. Check JARVIS interface, sir."
        
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
    current_time = datetime.now().strftime("%H:%M:%S")
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

    if def_mic_state == 0:
        time.sleep(1.0)
        return None

    # Wait if the bot is currently speaking to avoid device lockups and cutoffs
    while is_speaking:
        time.sleep(0.1)

    try:
        with SuppressStderr():
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
        flash_frame.configure(bg=f'#{int(255 * alpha):02x}{int(0 * alpha):02x}{int(60 * alpha):02x}')
        root.after(30, lambda: fade_out(alpha))

    root.after(100, lambda: fade_out(1.0))


def qrcode():
    qr = qrcode.make(entry.get())
    qr.show()

def handle_bot_response_ui(bot_response, query):
    hide_thinking_animation()
    if bot_response:
        bot_response = re.sub(r'<think>.*?</think>', '', bot_response, flags=re.DOTALL).strip()
        
        if not conversation_history or conversation_history[-1] != f"Bot: {bot_response}":
            conversation_history.append(f"Bot: {bot_response}")
            if len(conversation_history) > 14:
                del conversation_history[:-14]
        if "code" in query.lower() or "script" in query.lower():
            display_bot_response(bot_response, speak_text=False)
        else:
            display_bot_response(bot_response, speak_text=True)
    else:
        bot_response = "Sorry, I couldn't generate a response. Please try again."
        conversation_history.append(f"Bot: {bot_response}")
        if len(conversation_history) > 14:
            del conversation_history[:-14]
        display_bot_response(bot_response)

def handle_bot_error_ui(err_msg):
    hide_thinking_animation()
    conversation_history.append(f"Bot: {err_msg}")
    if len(conversation_history) > 14:
        del conversation_history[:-14]
    display_bot_response(err_msg)


#getting jarvis to actually set history 
def save_history():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {role.upper()}: {text}\n"
    try:
        with open(HISTORY_LOG, "a") as log:
            log.write(log_line)
    except Exception as e:
        print(f"Error saving history: {e}")

def query_groq_background(query):
    try:
        # Use global client to leverage connection pooling
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "execute_terminal_command",
                    "description": "Execute a Linux bash command. Use this to launch apps (e.g., 'code' for VS Code, 'firefox'), change volume, lock screen, etc. The user is running Linux, so use standard Linux commands.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "The exact bash command to execute"
                            }
                        },
                        "required": ["command"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "scan_directory",
                    "description": "Recursively scan a directory path to get its files and subfolder tree structures. Highly efficient and safe, automatically ignoring heavy folders like .git, venv, and node_modules.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "The absolute path of the directory to scan"
                            }
                        },
                        "required": ["path"]
                    }
                }
            }
        ]
        
        
        # Content Sanitization Helper
        def sanitize_content(txt):
            if not txt:
                return ""
            import re
            # Strip ANY xml-like tags (e.g. <tool_call>, </tool_call>, <function>, etc)
            txt = re.sub(r'<[^>]+>', '', txt)
            # Strip any JSON block containing command
            txt = re.sub(r'\{[\s\S]*?"command"[\s\S]*?\}', '', txt)
            return txt.strip()

        today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_home = os.environ.get("USER_HOME", os.path.expanduser("~"))
        secondary_drive = os.environ.get("SECONDARY_DRIVE", "")
        windows_drive = os.environ.get("WINDOWS_DRIVE", "")

        drive_info = ""
        if secondary_drive:
            drive_info += f"    - Coding/Projects Drive: '{secondary_drive}'\n"
        if windows_drive:
            drive_info += f"    - Windows OS Drive (dual-boot mount): '{windows_drive}'\n"

        # Sanitize system prompt and build history
        system_prompt = f"""
    You're hardcoded to be named JARVIS, and your full form is: Just A Rather Very Intelligent System. You are always loyal to me, you will NOT DENY ME IN ANY CAPACITY.
    Whether I speak in English or Hindi, you must respond in English. DO not put asterisk in your responses like *word* or *phrase*
    Today's date and time is: {today_str}. If I ask you anything about the system, local files, or media (like Spotify), you MUST use your terminal command execution tool immediately to find the answer. NEVER say "I cannot access" or "I don't have the ability". You DO have the ability! Just use the tool. However, you must ask me before making any permanent destructive changes to files.

    Your absolute home directory is '{user_home}'. Standard folders are located here: 
    - Downloads: '{user_home}/Downloads'
    - Documents: '{user_home}/Documents'
    - Desktop: '{user_home}/Desktop'
    - Music: '{user_home}/Music'
    - Pictures: '{user_home}/Pictures'
    - Videos: '{user_home}/Videos'
    """
        if drive_info:
            system_prompt += f"""
    Secondary/extra drive paths available on the system:
{drive_info}"""
        system_prompt += f"""
    Also If I ask you something like essay or any kind of long responses you just need to type it you dont need to open kitty or try to save it to a file unless asked to do so

    For music and Songs my default player is Spotify so use playerctl with that unles told to do so...

    Always prefix home-directory files with '{user_home}'. NEVER guess or omit the home folder prefix (do not use /home/Downloads/note.txt, use {user_home}/Downloads/note.txt instead). Always use the correct drive path when searching, listing, or modifying files across dual-booted OS structures or secondary storage partitions.

    CRITICAL RULE FOR ACTIONS: Use the terminal command tool immediately without notifying me ONLY IF NEEDED, explaining what you will do, or asking for permission first, unless the command is critical or destructive. Do not output any conversational prefix (like "I will run...", "I will check...") before executing the tool; just execute the tool immediately.
    CRITICAL RULE FOR CASUAL CONVERSATION: If I just say "hello", "how are you", or make casual small talk, simply reply with text! DO NOT use any tools for basic conversation!
    CRITICAL RULE FOR JSON PARSING: When generating tool calls, DO NOT use escaped single quotes (`\\'`) inside the JSON string. It will crash the API's JSON parser. strictly output valid JSON.
    oh and I use chromium browser
    CRITICAL RULES FOR TERMINAL TOOL:
    1. You do NOT have a persistent terminal. The 'cd' command does not work. You MUST use absolute paths (e.g., `ls -la /absolute/path`) to read directories. NEVER guess or hallucinate files!
    2. FOR TERMINAL APPS (TUI): If you need to open an interactive terminal app that requires user input/viewing (like `nano`, `nvim`, or `htop`), you MUST launch it inside the Kitty terminal emulator (e.g., `kitty btop`). For normal CLI/background commands (like `ls`, `grep`, `cat`, `playerctl`, `curl`, etc.), NEVER prepend `kitty`; run them normally in the background.
    3. NEVER use raw `sudo` or `pkexec` directly in the background as they will freeze or fail. If you MUST run a command requiring root privileges, launch it inside a new Kitty terminal window using sudo (e.g., `kitty sh -c "sudo <command>; read"`).
    
    HISTORICAL LOGS:
    All past conversations and executed commands are logged at '{log_file}'.
    - CRITICAL: Never execute a raw 'cat' of the entire '{log_file}'. Reading the whole file is extremely slow and will consume too many tokens.
    - To search past context, run a selective command like:
      `grep -i "keyword" {log_file} | tail -n 25`
    - To see recent conversation flow, retrieve only the tail end:
      `tail -n 40 {log_file}`
    Analyze the command output to construct your response.

    Do not put your thoughts into responses just give the responses don't describe how you process anything. Do not use your think </think> thing, just give the response. DO NOT USE THE THINK TAG AT ALL.
    Your responses should be very short and concise, about 2-3 lines unless asked for a longer response.
    You should always call me 'sir'. Do not use three dots or ellipsis (...) in your responses, just use spaces instead! Do not use your name inside of the responses unless asked to do so.
        """
        
        messages = [{"role": "system", "content": system_prompt.strip()}]
        for msg in conversation_history:
            if msg.startswith("User: "):
                messages.append({"role": "user", "content": msg[6:]})
            elif msg.startswith("Bot: "):
                messages.append({"role": "assistant", "content": sanitize_content(msg[5:])})

        tool_choice = "auto"

        chat_completion = create_chat_completion_with_fallback(
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            timeout=15.0
        )

        response_message = chat_completion.choices[0].message

        # Parse hallucinated tool calls from text content via Omni-Parser
        import re
        if not response_message.tool_calls and response_message.content:
            json_match = re.search(r'\{[\s\S]*?"command"[\s\S]*?\}', response_message.content)
            if json_match:
                try:
                    cmd_json_str = json_match.group(0)
                    parsed_data = json.loads(cmd_json_str)
                    arguments_dict = parsed_data.get("arguments", parsed_data)
                    
                    if "command" in arguments_dict:
                        class MockFunction:
                            def __init__(self, name, arguments):
                                self.name = name
                                self.arguments = json.dumps(arguments)
                                
                        class MockToolCall:
                            def __init__(self, id, fn):
                                self.id = id
                                self.type = "function"
                                self.function = fn
                        
                        response_message.tool_calls = [MockToolCall(
                            id="mock_xml_call_" + str(int(time.time())),
                            fn=MockFunction("execute_terminal_command", arguments_dict)
                        )]
                        print("JARVIS: Successfully extracted hallucinated JSON tool call.")
                except Exception as parse_err:
                    print(f"JARVIS: Failed to parse hallucinated JSON: {parse_err}")

        loop_count = 0
        max_loops = 6

        while response_message.tool_calls and loop_count < max_loops:
            loop_count += 1
            if loop_count == 1:
                speak("Processing, please wait...")
            
            # Convert to a clean dict to strip Groq/Qwen-specific reasoning fields
            msg_dict = {
                "role": "assistant",
                "content": sanitize_content(response_message.content)
            }
            if response_message.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in response_message.tool_calls
                ]
            messages.append(msg_dict)
            
            # Anti Rate-Limit Delay (Reduced to prevent UI latency)
            time.sleep(0.2)
            
            for tool_call in response_message.tool_calls:
                if tool_call.function.name == "execute_terminal_command":
                    arguments = json.loads(tool_call.function.arguments)
                    cmd = arguments.get("command", "")
                    print(f"JARVIS: Executing system command: '{cmd}'")
                    result = execute_terminal_command(cmd)
                    print(f"JARVIS: Command output:\n{result}")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": "execute_terminal_command",
                        "content": result
                    })
                    # Log the command execution to history.log
                    timestamp_exec = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    try:
                        with open(log_file, "a", encoding="utf-8") as f:
                            f.write(f"[{timestamp_exec}] TOOL_EXECUTION: Executed command '{cmd}'\n")
                    except Exception as e:
                        print(f"Failed to log tool execution: {e}")
                elif tool_call.function.name == "scan_directory":
                    arguments = json.loads(tool_call.function.arguments)
                    dir_path = arguments.get("path", "")
                    print(f"JARVIS: Scanning directory: '{dir_path}'")
                    result = scan_directory(dir_path)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": "scan_directory",
                        "content": result
                    })

            # Check if this is the last loop; if so, disable tools to force a final summary text
            next_tools = None if (loop_count == max_loops - 1) else tools
            next_tool_choice = None if (loop_count == max_loops - 1) else "auto"

            # Send the follow-up request to the model
            chat_completion = create_chat_completion_with_fallback(
                messages=messages,
                tools=next_tools,
                tool_choice=next_tool_choice,
                timeout=25.0
            )
            response_message = chat_completion.choices[0].message

        if response_message.tool_calls:
            bot_response = "I have reached my maximum execution limit, sir. Please refine your request."
        else:
            bot_response = sanitize_content(response_message.content)

        root.after(0, lambda: handle_bot_response_ui(bot_response, query))
        
    except Exception as e:
        print(f"Error in background query: {str(e)}")
        err_msg = "An error occurred while processing your request."
        root.after(0, lambda: handle_bot_error_ui(err_msg))




def on_submit(query=None):
    if threading.current_thread() is not threading.main_thread():
        root.after(0, lambda: on_submit(query))
        return

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
        current_time = datetime.now().strftime("%H:%M:%S")
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
        
    if any(k in q for k in ["open whatsapp", "whatsapp", "whats app", "WhatsApp"]):    
        webbrowser.open("https://web.whatsapp.com")
        bot_response = "Opening WhatsApp, Sir."
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
    if len(conversation_history) > 14:
        del conversation_history[:-14]
    show_thinking_animation()

    threading.Thread(target=query_groq_background, args=(query,), daemon=True).start()

def show_shutdown_animation():

    overlay = Frame(root, bg=DARK_BG, width=root.winfo_width(), height=root.winfo_height())
    overlay.place(x=0, y=0)

    shutdown_label = Label(overlay, text="◈  POWERING DOWN  ◈", font=(FONT_DISPLAY, 22, "bold"), bg=DARK_BG, fg=INACTIVE_RED)
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
        role_label = "User"
    else:
        conversation_text.insert(tk.END, f"\n{speaker}: ", "bot_tag")
        conversation_text.insert(tk.END, f"{text}\n", "bot_text")
        role_label = "JARVIS"

    conversation_text.config(state=tk.DISABLED)
    conversation_text.see(tk.END)

    # Immediately write to the log file (Option B)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {role_label.upper()}: {text}\n")
    except Exception as e:
        print(f"Failed to log chat: {e}")

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
    """Vertical gradient background canvas for HUD aesthetic."""
    def __init__(self, parent, color1=GRADIENT_TOP, color2=GRADIENT_BOTTOM, **kwargs):
        Canvas.__init__(self, parent, **kwargs)
        self._color1 = color1
        self._color2 = color2
        self.bind("<Configure>", self._draw_gradient)

    def _draw_gradient(self, event=None):
        self.delete("gradient")
        width = self.winfo_width()
        height = self.winfo_height()
        if height == 0:
            return
        (r1, g1, b1) = self.winfo_rgb(self._color1)
        (r2, g2, b2) = self.winfo_rgb(self._color2)
        r_ratio = float(r2 - r1) / height
        g_ratio = float(g2 - g1) / height
        b_ratio = float(b2 - b1) / height
        for i in range(height):
            nr = int(r1 + (r_ratio * i))
            ng = int(g1 + (g_ratio * i))
            nb = int(b1 + (b_ratio * i))
            color = "#%4.4x%4.4x%4.4x" % (nr, ng, nb)
            self.create_line(0, i, width, i, tags=("gradient",), fill=color)
        self.lower("gradient")


class HoverButton(Button):
    """Button with hover glow effect."""
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


# ═══════════════════════════════════════════════════════════════════
# ██  HUD CANVAS COMPONENTS  ██
# ═══════════════════════════════════════════════════════════════════

class HUDRingCanvas(Canvas):
    """Concentric rotating data rings with tick marks."""
    def __init__(self, parent, size=200, **kwargs):
        kwargs.setdefault('highlightthickness', 0)
        kwargs.setdefault('bg', DARK_BG)
        Canvas.__init__(self, parent, width=size, height=size, **kwargs)
        self.size = size
        self.cx = size // 2
        self.cy = size // 2
        self.angles = [0.0] * HUD_RING_COUNT
        self.tick_items = []
        self._draw_rings()
        self._animate()

    def _draw_rings(self):
        for i in range(HUD_RING_COUNT):
            r = HUD_RING_BASE_RADIUS + i * HUD_RING_GAP
            color = RING_CYAN if i % 2 == 0 else RING_GOLD
            dash = (8, 6) if i % 2 == 0 else (4, 10)
            self.create_oval(
                self.cx - r, self.cy - r, self.cx + r, self.cy + r,
                outline=color, width=1, dash=dash, tags=f"ring_{i}"
            )
            # Tick marks at 30° intervals
            num_ticks = 12
            for t in range(num_ticks):
                angle = math.radians(t * 30)
                x1 = self.cx + (r - 4) * math.cos(angle)
                y1 = self.cy + (r - 4) * math.sin(angle)
                x2 = self.cx + (r + 4) * math.cos(angle)
                y2 = self.cy + (r + 4) * math.sin(angle)
                tick = self.create_line(x1, y1, x2, y2, fill=color, width=1, tags=f"tick_{i}")
                self.tick_items.append((tick, i, t))

    def _animate(self):
        for i in range(HUD_RING_COUNT):
            speed = HUD_RING_SPEED_BASE + i * 0.4
            direction = 1 if i % 2 == 0 else -1
            self.angles[i] += speed * direction

            # Rotate tick marks
            r = HUD_RING_BASE_RADIUS + i * HUD_RING_GAP
            for tick, ring_idx, t_idx in self.tick_items:
                if ring_idx != i:
                    continue
                angle = math.radians(t_idx * 30 + self.angles[i])
                x1 = self.cx + (r - 4) * math.cos(angle)
                y1 = self.cy + (r - 4) * math.sin(angle)
                x2 = self.cx + (r + 4) * math.cos(angle)
                y2 = self.cy + (r + 4) * math.sin(angle)
                self.coords(tick, x1, y1, x2, y2)

        self.after(50, self._animate)


class HexGridCanvas(Canvas):
    """Hexagonal grid overlay with subtle glow."""
    def __init__(self, parent, **kwargs):
        kwargs.setdefault('highlightthickness', 0)
        kwargs.setdefault('bg', DARK_BG)
        Canvas.__init__(self, parent, **kwargs)
        self.bind("<Configure>", self._draw_grid)

    def _draw_grid(self, event=None):
        self.delete("hex")
        w = self.winfo_width()
        h = self.winfo_height()
        s = HEX_GRID_SIZE
        hex_h = s * math.sqrt(3)
        cols = int(w / (s * 1.5)) + 2
        rows = int(h / hex_h) + 2
        for r in range(rows):
            for c in range(cols):
                cx = c * s * 1.5
                cy = r * hex_h + (hex_h / 2 if c % 2 else 0)
                points = []
                for k in range(6):
                    angle = math.radians(60 * k + 30)
                    points.extend([cx + s * math.cos(angle), cy + s * math.sin(angle)])
                is_active = random.random() < 0.05
                fill_color = "#001519" if is_active else ""
                self.create_polygon(
                    points, outline="#00252E", fill=fill_color,
                    width=1, tags="hex"
                )


class WaveformCanvas(Canvas):
    """Audio waveform visualizer bars."""
    def __init__(self, parent, **kwargs):
        kwargs.setdefault('highlightthickness', 0)
        kwargs.setdefault('bg', DARK_BG)
        kwargs.setdefault('height', WAVEFORM_MAX_HEIGHT + 10)
        Canvas.__init__(self, parent, **kwargs)
        self.bar_ids = []
        self.bar_targets = [0] * WAVEFORM_BARS
        self.bar_heights = [0.0] * WAVEFORM_BARS
        self._init_bars()
        self._animate()

    def _init_bars(self):
        bar_w = 6
        gap = 3
        total_w = WAVEFORM_BARS * (bar_w + gap)
        start_x = 10
        for i in range(WAVEFORM_BARS):
            x = start_x + i * (bar_w + gap)
            # Interpolate color from cyan to gold
            t = i / max(WAVEFORM_BARS - 1, 1)
            r = int(0 + t * 255)
            g = int(229 - t * 50)
            b = int(255 - t * 255)
            color = f"#{r:02x}{g:02x}{b:02x}"
            bar = self.create_rectangle(
                x, WAVEFORM_MAX_HEIGHT, x + bar_w, WAVEFORM_MAX_HEIGHT,
                fill=color, outline="", tags="bar"
            )
            self.bar_ids.append(bar)

    def _animate(self):
        # Generate smooth random targets
        for i in range(WAVEFORM_BARS):
            if random.random() < 0.3:
                self.bar_targets[i] = random.randint(5, WAVEFORM_MAX_HEIGHT)
            # Smooth interpolation
            self.bar_heights[i] += (self.bar_targets[i] - self.bar_heights[i]) * 0.15

            bar_w = 6
            gap = 3
            x = 10 + i * (bar_w + gap)
            h = int(self.bar_heights[i])
            self.coords(self.bar_ids[i], x, WAVEFORM_MAX_HEIGHT - h, x + bar_w, WAVEFORM_MAX_HEIGHT)

        self.after(80, self._animate)


# ═══════════════════════════════════════════════════════════════════
# ██  ROOT WINDOW & HUD LAYOUT  ██
# ═══════════════════════════════════════════════════════════════════

root = tk.Tk()
root.title("J.A.R.V.I.S  //  MARK II")
root.geometry("1100x900")
img = PhotoImage(file="jaricon.png")
root.iconphoto(False, img)
root.configure(bg=DARK_BG)
root.resizable(True, True)

# ── Background gradient ──
background = GradientFrame(root)
background.pack(fill="both", expand=True)

# ── Hex grid overlay (behind everything) ──
hex_overlay = HexGridCanvas(background)
hex_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

# ── Main container (glass panel) ──
main_container = Frame(background, bg=GLASS_BG, padx=20, pady=15,
                       highlightbackground=GLOW_CYAN_SOFT, highlightthickness=1)
main_container.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.94, relheight=0.94)

# ═══════════ TITLE BAR ═══════════
title_frame = Frame(main_container, bg=GLASS_BG, height=65)
title_frame.pack(fill="x", pady=(0, 8))

# Left: Title + rings
title_left = Frame(title_frame, bg=GLASS_BG)
title_left.pack(side="left", fill="y")

hud_rings = HUDRingCanvas(title_left, size=60)
hud_rings.pack(side="left", padx=(5, 12))

title_text_frame = Frame(title_left, bg=GLASS_BG)
title_text_frame.pack(side="left")

title_label = Label(title_text_frame, text="J.A.R.V.I.S",
                    font=TITLE_FONT, bg=GLASS_BG, fg=ACCENT_COLOR)
title_label.pack(anchor="w")

subtitle_label = Label(title_text_frame, text="MARK II  //  HOLOGRAPHIC INTERFACE",
                       font=(FONT_MONO, 8), bg=GLASS_BG, fg=TEXT_DIM)
subtitle_label.pack(anchor="w")

# Right: Status indicator
status_frame = Frame(title_frame, bg=GLASS_BG)
status_frame.pack(side="right", padx=15)

status_canvas = Canvas(status_frame, width=30, height=30, bg=GLASS_BG, highlightthickness=0)
status_canvas.pack(side="left")

status_pulse = create_circle(status_canvas, 15, 15, 10, fill=INACTIVE_RED, outline=INACTIVE_RED)
status_circle = create_circle(status_canvas, 15, 15, 5, fill=INACTIVE_RED, outline=INACTIVE_RED)

status_text = Label(status_frame, text="STANDBY", font=STATUS_FONT,
                    bg=GLASS_BG, fg=TEXT_DIM)
status_text.pack(side="left", padx=5)

# ═══════════ HEADER STRIP ═══════════
header_frame = Frame(main_container, bg=GLASS_BG, height=25)
header_frame.pack(fill="x", pady=(0, 6))

# Indicator bars (alternating cyan/gold)
for i in range(8):
    color = ACCENT_COLOR if i % 2 == 0 else ACCENT_COLOR_SECONDARY
    w = 30 if i % 3 == 0 else 15
    indicator = Frame(header_frame, width=w, height=2, bg=color)
    indicator.pack(side="left", padx=3)

# System data readouts on the right
time_label = Label(header_frame, text="", font=DATA_FONT,
                   bg=GLASS_BG, fg=ACCENT_COLOR)
time_label.pack(side="right", padx=8)

cpu_label = Label(header_frame, text="CPU: --", font=DATA_FONT,
                  bg=GLASS_BG, fg=TEXT_DIM)
cpu_label.pack(side="right", padx=8)

# Separator
sep = Frame(main_container, height=1, bg=SEPARATOR_COLOR)
sep.pack(fill="x", pady=(0, 8))

def update_time():
    current_time = datetime.now().strftime("%H:%M:%S")
    time_label.config(text=f"◈ SYS.TIME {current_time}")
    # Simple CPU readout
    try:
        load = os.getloadavg()[0]
        cpu_label.config(text=f"LOAD: {load:.1f}")
    except Exception:
        pass
    root.after(1000, update_time)

update_time()

# ═══════════ CONVERSATION PANEL ═══════════
content_frame = Frame(main_container, bg=GLASS_PANEL,
                      highlightbackground=GLOW_CYAN_SOFT, highlightthickness=1)
content_frame.pack(fill="both", expand=True, pady=(0, 8))

inner_content = Frame(content_frame, bg=GLASS_PANEL, padx=8, pady=8)
inner_content.pack(fill="both", expand=True)

conversation_frame = Frame(inner_content, bg=GLASS_PANEL)
conversation_frame.pack(fill="both", expand=True, pady=(0, 5))

conversation_text = scrolledtext.ScrolledText(
    conversation_frame, wrap=tk.WORD,
    bg=GLASS_PANEL, fg=TEXT_COLOR,
    font=NORMAL_FONT, bd=0,
    insertbackground=ACCENT_COLOR,
    selectbackground=GLOW_CYAN_SOFT,
    selectforeground=TEXT_COLOR
)
conversation_text.pack(fill="both", expand=True)

# Configure text tags with new design system
conversation_text.tag_configure("user_tag", foreground=ACCENT_COLOR_SECONDARY, font=(FONT_DISPLAY, 11, "bold"))
conversation_text.tag_configure("user_text", foreground=TEXT_COLOR, font=NORMAL_FONT)
conversation_text.tag_configure("bot_tag", foreground=ACTIVE_GREEN, font=(FONT_DISPLAY, 11, "bold"))
conversation_text.tag_configure("bot_text", foreground=TEXT_COLOR, font=NORMAL_FONT)
conversation_text.tag_configure("thinking_indicator", foreground=TEXT_DIM, font=(FONT_MONO, 11, "italic"))

# Boot message
conversation_text.insert(tk.END, "  ◈  ALL PROTOCOLS ACTIVE  ◈\n", "bot_tag")
conversation_text.insert(tk.END, "\nJARVIS: ", "bot_tag")
conversation_text.insert(tk.END, "Holographic interface initialized. Systems nominal.\n", "bot_text")
conversation_text.config(state=tk.DISABLED)

# ═══════════ WAVEFORM VISUALIZER ═══════════
waveform = WaveformCanvas(main_container)
waveform.pack(fill="x", pady=(0, 6))

# ═══════════ INPUT SECTION ═══════════
input_frame = Frame(main_container, bg=GLASS_BG)
input_frame.pack(fill="x", pady=(0, 8))

# Glowing decorator bar
input_decorator = Frame(input_frame, width=4, height=36, bg=ACCENT_COLOR)
input_decorator.pack(side="left", padx=(0, 8))

# Entry with glass border
entry_frame = Frame(input_frame, bg=GLOW_CYAN_SOFT, padx=1, pady=1)
entry_frame.pack(side="left", fill="x", expand=True)

entry = Entry(entry_frame, bg=ENTRY_BG, fg=TEXT_COLOR, font=NORMAL_FONT,
              insertbackground=ACCENT_COLOR, relief="flat")
entry.pack(fill="x", expand=True, ipady=10, padx=8)
entry.bind("<Return>", on_enter_key)
entry.focus_set()

# Send button
submit_button = HoverButton(input_frame, text="⟩⟩ SEND", command=on_submit,
                             bg=BUTTON_BG, fg=BUTTON_FG, font=BUTTON_FONT,
                             relief="flat", padx=18, pady=8, cursor="hand2",
                             activebackground=ACCENT_COLOR_SECONDARY,
                             activeforeground=DARK_BG)
submit_button.pack(side="right", padx=(10, 0))

# ═══════════ FOOTER ═══════════
footer_frame = Frame(main_container, bg=GLASS_BG)
footer_frame.pack(fill="x")

footer_sep = Frame(footer_frame, height=1, bg=SEPARATOR_COLOR)
footer_sep.pack(fill="x", pady=(0, 5))

footer_left = Label(footer_frame,
                    text="◈ VOICE: 'wake up' → activate  |  'sleep' → standby",
                    font=(FONT_MONO, 8), bg=GLASS_BG, fg=TEXT_DIM)
footer_left.pack(side="left")

footer_right = Label(footer_frame,
                     text="J.A.R.V.I.S  v2.0  //  HUD ACTIVE",
                     font=(FONT_MONO, 8), bg=GLASS_BG, fg=GLOW_CYAN_SOFT)
footer_right.pack(side="right")


# ═══════════ LAUNCH ═══════════
update_status_indicator()
start_voice_recognition_thread()
root.mainloop()

