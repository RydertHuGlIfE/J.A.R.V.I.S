import google.generativeai as genai
import sys
import tkinter as tk
from tkinter import messagebox
import webbrowser
import os
import pyautogui
import whisper
import speech_recognition as sr
import pyttsx3
import threading
from PIL import ImageGrab
import time


conversation_history = []
recognizer = sr.Recognizer()
tts_engine = pyttsx3.init()

HEAD_COLOR = "#0c0536"  
BACKGROUND_COLOR = "#0c0536"  
FONT_COLOR = "#FFA500"  
FOREGROUND_COLOR = "#222224"

FONT_NAME = "Arial"  
FONT_SIZE = 12 
is_bot_active = False

voices = tts_engine.getProperty('voices')
tts_engine.setProperty('voice', voices[0].id)

def type_message(message):
    pyautogui.typewrite(message, interval=0.2)

def rgn():
    if len(conversation_history) >= 2:
        last_query = conversation_history[-2].split("User: ", 1)[-1]
        entry.delete(0, tk.END)
        entry.insert(0, last_query)
        on_submit()

def speak(text):
    tts_engine.say(text)
    tts_engine.runAndWait()

def update_status_indicator():
    if is_bot_active:
        status_label.config(text="Status: Active", fg="green")
    else:
        status_label.config(text="Status: Standby", fg="red")

def recognize_voice():
    global is_bot_active
    
    try:
        with sr.Microphone() as source:
            print("Listening...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)  
            
            try:
                audio = recognizer.listen(source, timeout=7, phrase_time_limit=7)  
                
                try:
                    query = recognizer.recognize_google(audio)
                    print(f"You said: {query}")
                    
                    if "wake up"in query.lower() and not is_bot_active:
                        is_bot_active = True
                        update_status_indicator()
                        display_bot_response("I'm online and ready sir!" or "At your service sir!", speak_text=True)
                        return None
                    
                    elif "sleep" in query.lower() and is_bot_active:
                        is_bot_active = False
                        update_status_indicator()
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
    
def on_submit(query=None):
    global is_bot_active
    if not is_bot_active and query is None:
        is_bot_active = True
        update_status_indicator()
        display_bot_response("I am Online sir.", speak_text=True)
    
    if query is None:
        query = entry.get()
    
    if not is_bot_active and query is not None:
        return

    if query.lower() == 'exit' or query.lower() == 'good bye':
        root.destroy()
        sys.exit()
    if "mark calculator" in query.lower() or "marks calculator" in query.lower():
        os.startfile("D:\\Coding\\Python\\Gemini AI APP\\GPAC.py")
        bot_response = "Opening CGPA Calculator, Sir!"
        display_bot_response(bot_response)
        return
    if "image search" in query.lower():
        webbrowser.open("lens.google.com")
        time.sleep(3)
        pyautogui.hotkey('ctrl', 'v')
        return
    
    if "screenshot" in query.lower():
        screenshot = ImageGrab.grab()
        screenshot.save("screenshot.png")
        bot_response = "Screenshot saved, replacing any existing screenshot with the same name."             
        display_bot_response(bot_response)
        return 
    if "vs code" in query.lower() or "code editor" in query.lower():
        os.startfile("C:\\Users\\chauh\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Visual Studio Code\\Visual Studio Code.lnk")
        bot_response = "Opening Code Editor, Sir."
        display_bot_response(bot_response)
        return
    if query.lower().startswith('search youtube for '):
        search_query = query[14:]
        search_url = f"https://www.youtube.com/results?search_query={search_query.replace(' ', '+')}"
        webbrowser.open(search_url)
        bot_response = f"Searching YouTube for: {search_query}"
        display_bot_response(bot_response)
        return
    if "speed test" in query.lower():
        webbrowser.open("https://speedtest.net/run#")
        bot_response = "Opening Speed Test, Sir."
        display_bot_response(bot_response)
        return
    if "google" in query.lower():
        search_query = query[query.lower().index("google") + 6:].strip()
        url = f"https://www.google.com/search?q={search_query}"
        bot_response = "Googling Your Query."
        display_bot_response(bot_response)
        webbrowser.open(url)
        return 
    if "notes" in query.lower():
        os.startfile("D:\\Coding\\Python\\Gemini AI APP\\notes.py")
        bot_response = "Opening the Vast Note Collection, Sir."
        display_bot_response(bot_response)
        return
    if "club" in query.lower():
        webbrowser.open("https://www.srmup.in/cpage.aspx?mpgid=6&pgidtrail=44")
        bot_response = "Opening the Detailed Club list."
        display_bot_response(bot_response)
        return

    conversation_history.append(f"User: {query}") 

    try:
        genai.configure(api_key="AIzaSyBdjs-Cyq53rr8Gj8SSPvCJSHNoFw4ahi0")
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "max_output_tokens": 150
        }
        model = genai.GenerativeModel("models/gemini-1.5-flash", generation_config=generation_config)
        system_prompt = """
        You're hardcoded to be named JARVIS.
        Whether I speak in English or Hindi, you must respond in English.
        Your responses should be very short and concise, about 2-3 lines unless asked for a longer response.
        You should always call me 'sir'.
        """
        conversation_input = system_prompt + "\n\n" + "\n".join(conversation_history)
        response = model.generate_content([conversation_input])
        
        if response.candidates and hasattr(response.candidates[0], 'content'):
            content = response.candidates[0].content
            if hasattr(content, 'parts') and content.parts:
                bot_response = content.parts[0].text
                if not conversation_history or conversation_history[-1] != f"Bot: {bot_response}":
                    conversation_history.append(f"Bot: {bot_response}")
                if "code" in query.lower() or "script" in query.lower():
                    display_bot_response(bot_response, speak_text=False)
                else:
                    display_bot_response(bot_response, speak_text=True)
            else:
                bot_response = "Sorry, I couldn't generate a response. Please try again."
                conversation_history.append(f"Bot: {bot_response}")
                display_bot_response(bot_response)
        else:
            bot_response = "Sorry, I couldn't generate a response. Please try again."
            conversation_history.append(f"Bot: {bot_response}")
            display_bot_response(bot_response)
    except Exception as e:
        print(f"Error: {str(e)}")
        bot_response = "An error occurred while processing your request."
        conversation_history.append(f"Bot: {bot_response}")
        display_bot_response(bot_response)

def display_bot_response(response, speak_text=True):
    bot_text.delete(1.0, tk.END)
    bot_text.insert(tk.END, response)
    bot_text.see(tk.END)
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

root = tk.Tk()
root.title("Gemini AI App")
root.geometry("800x600")

root.configure(bg=BACKGROUND_COLOR)

status_label = tk.Label(root, text="Status: Standby", bg=BACKGROUND_COLOR, fg="red", font=(FONT_NAME, 14, 'bold'))
status_label.pack(pady=5)

entry = tk.Entry(root, width=70, bg=FOREGROUND_COLOR, fg=FONT_COLOR, font=(FONT_NAME, FONT_SIZE))
entry.pack(pady=10)

submit_button = tk.Button(root, text="Submit", command=on_submit, bg=HEAD_COLOR, fg=FONT_COLOR, font=('Comic Sans', '20'))
submit_button.pack(pady=5)

bot_text = tk.Text(root, wrap=tk.WORD, bg=FOREGROUND_COLOR, fg=FONT_COLOR, font=(FONT_NAME, FONT_SIZE))
bot_text.pack(pady=10)

# Display initial standby message
bot_text.insert(tk.END, "I'm in standby mode. Say 'wake up' to activate me.")

start_voice_recognition_thread()
root.mainloop()