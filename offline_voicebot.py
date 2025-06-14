import tkinter as tk
from tkinter import ttk
import pyttsx3
import sounddevice as sd
import queue
import json
import threading
import time
from vosk import Model, KaldiRecognizer

# ========== GLOBAL STATE ==========
engine = pyttsx3.init()
engine.setProperty('rate', 150)

model = Model("model")
recognizer = KaldiRecognizer(model, 16000)
q = queue.Queue()
listening = False
device_index = None  # Default, will be selected from dropdown

# ========== TTS ==========
def speak(text):
    output_text.insert(tk.END, f"Bot: {text}\n")
    output_text.see(tk.END)
    engine.say(text)
    engine.runAndWait()

# ========== Chatbot Logic ==========
def get_bot_response(user_input):
    user_input = user_input.lower()
    if "hello" in user_input:
        return "Hello! How can I assist you today?"
    elif "your name" in user_input:
        return "I am your offline assistant."
    elif "how are you" in user_input:
        return "I'm functioning perfectly!"
    elif "bye" in user_input:
        return "Goodbye! Have a nice day!"
    else:
        return "Sorry, I didn't understand that."

# ========== Text Input ==========
def handle_text_input():
    user_text = user_entry.get()
    if not user_text.strip():
        return
    output_text.insert(tk.END, f"You: {user_text}\n")
    output_text.see(tk.END)
    user_entry.delete(0, tk.END)
    response = get_bot_response(user_text)
    speak(response)

# ========== Voice Thread ==========
def listen_voice():
    threading.Thread(target=voice_input_worker, daemon=True).start()

def voice_input_worker():
    global listening
    listening = True
    speak("Listening for 8 seconds...")
    try:
        with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                               channels=1, device=device_index, callback=callback):
            start_time = time.time()
            while time.time() - start_time < 8:
                if not listening:
                    break
                try:
                    data = q.get(timeout=1)
                except queue.Empty:
                    continue
                if recognizer.AcceptWaveform(data):
                    result = recognizer.Result()
                    print("Vosk:", result)
                    text = json.loads(result)["text"]
                    if text:
                        user_entry.delete(0, tk.END)
                        user_entry.insert(0, text)
                        root.after(100, handle_text_input)
                        break
    except Exception as e:
        print("Error:", e)

# ========== Callback ==========
def callback(indata, frames, time_info, status):
    if status:
        print("Audio Status:", status)
    q.put(bytes(indata))

# ========== Exit ==========
def safe_exit():
    global listening
    listening = False
    speak("Shutting down. Goodbye!")
    root.after(1000, root.destroy)

# ========== Mic Test ==========
def mic_test():
    threading.Thread(target=mic_test_worker, daemon=True).start()

def mic_test_worker():
    try:
        speak("Mic test starting. Speak for 5 seconds.")
        with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                               channels=1, device=device_index, callback=callback):
            start_time = time.time()
            while time.time() - start_time < 5:
                try:
                    data = q.get(timeout=1)
                except queue.Empty:
                    continue
                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    msg = result["text"]
                    if msg:
                        print("Mic Test Heard:", msg)
                        speak("I heard: " + msg)
                        return
        speak("Mic test finished.")
    except Exception as e:
        print("Mic test error:", e)

# ========== Device Selector ==========
def load_devices():
    devices = sd.query_devices()
    input_devices = [d['name'] for d in devices if d['max_input_channels'] > 0]
    return input_devices

def set_selected_device(event):
    global device_index
    selected_name = mic_device_combo.get()
    for i, dev in enumerate(sd.query_devices()):
        if dev['name'] == selected_name:
            device_index = i
            break
    print("Selected mic:", selected_name, "| Index:", device_index)

# ========== GUI ==========
root = tk.Tk()
root.title("Offline Chatbot & Voice Assistant")
root.geometry("600x600")

frame = tk.Frame(root)
frame.pack(pady=10)

output_text = tk.Text(frame, height=20, width=70, wrap=tk.WORD)
output_text.pack()

user_entry = tk.Entry(root, font=('Arial', 14), width=50)
user_entry.pack(pady=10)

btn_frame = tk.Frame(root)
btn_frame.pack(pady=5)

send_button = tk.Button(btn_frame, text="Send", command=handle_text_input)
send_button.grid(row=0, column=0, padx=10)

voice_button = tk.Button(btn_frame, text="🎤 Voice", command=listen_voice)
voice_button.grid(row=0, column=1)

mic_test_button = tk.Button(btn_frame, text="🎧 Mic Test", command=mic_test)
mic_test_button.grid(row=0, column=2, padx=10)

exit_button = tk.Button(btn_frame, text="Exit", command=safe_exit)
exit_button.grid(row=0, column=3, padx=10)

# Mic device selection
mic_label = tk.Label(root, text="Select Microphone:")
mic_label.pack()

mic_device_combo = ttk.Combobox(root, values=load_devices(), width=60)
mic_device_combo.pack()
mic_device_combo.bind("<<ComboboxSelected>>", set_selected_device)
mic_device_combo.current(0)  # Select first mic by default
set_selected_device(None)  # Initialize device index

root.mainloop()