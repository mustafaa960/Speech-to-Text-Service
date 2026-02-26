"""
Speech-to-Text Service (Faster-Whisper / Offline)

A lightweight Windows background service that converts speech to text using
Faster-Whisper. Press F9 to record, and your words are automatically typed
into the active window.

Features:
    - 100% offline speech-to-text (no internet required)
    - Multi-language support (English & Iraqi Arabic)
    - Smart silence detection with configurable thresholds
    - Animated floating UI with loading indicator
    - System tray integration

Keyboard Shortcuts:
    F9  : Start recording
    F10 : Toggle language (English / Arabic)

Author: Mustafa
License: MIT
"""

import math
import os
import queue
import random
import sys
import tempfile
import threading
import time
import wave

import keyboard
import numpy as np
import pyperclip
import pystray
import sounddevice as sd
from faster_whisper import WhisperModel
from PIL import Image, ImageDraw

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

# Whisper Model
MODEL_SIZE = "medium"        # Options: tiny, base, small, medium, large-v3
COMPUTE_TYPE = "int8"        # INT8 quantization for faster CPU inference

# Audio Recording
SAMPLE_RATE = 16000          # Whisper expects 16kHz audio
CHANNELS = 1                 # Mono recording
CHUNK_DURATION = 0.5         # Record in 0.5-second chunks

# Silence Detection
SILENCE_THRESHOLD = 0.003    # RMS energy below this level = silence
SILENCE_TIMEOUT = 3.5        # Seconds of silence before auto-stopping
MAX_RECORD_DURATION = 120    # Maximum recording length (seconds)
INITIAL_TIMEOUT = 15         # Seconds to wait for first speech

# Languages: (Display Name, Whisper Code, UI Abbreviation)
LANGUAGES = [
    ("English", "en", "EN"),
    ("Arabic (Iraq)", "ar", "AR"),
]

# Arabic dialect hint for better Iraqi Arabic recognition
ARABIC_PROMPT = "this is arabic language iraqi"

# UI Theme
THEME_BG = "#1a1a1a"
COLOR_GREEN = "#b3e64d"
COLOR_BLUE = "#00aaff"
COLOR_ORANGE = "#ff9f43"
COLOR_RED = "#ff4444"

# ─────────────────────────────────────────────────────────────────────────────
# Application State
# ─────────────────────────────────────────────────────────────────────────────

whisper_model = None
model_loaded = False
is_listening = False
recording_active = False
current_lang_idx = 0

ui_queue = queue.Queue()
audio_queue = queue.Queue()


# ─────────────────────────────────────────────────────────────────────────────
# Model Loading
# ─────────────────────────────────────────────────────────────────────────────

def load_model():
    """Load the Whisper model in a background thread with UI feedback."""
    global whisper_model, model_loaded

    print(f"[Model] Loading Faster-Whisper '{MODEL_SIZE}' model...")
    ui_queue.put(("LOADING_START", ""))

    try:
        whisper_model = WhisperModel(MODEL_SIZE, device="cpu", compute_type=COMPUTE_TYPE)
        model_loaded = True
        print("[Model] Model loaded successfully!")
        ui_queue.put(("LOADING_DONE", ""))
    except Exception as e:
        print(f"[Model] FATAL: Failed to load model: {e}")
        ui_queue.put(("LOADING_FAIL", str(e)))


# ─────────────────────────────────────────────────────────────────────────────
# Audio Recording
# ─────────────────────────────────────────────────────────────────────────────

def record_until_silence():
    """
    Record audio from the microphone until silence is detected.

    Uses RMS energy to detect speech vs. silence. Recording starts
    immediately and stops after SILENCE_TIMEOUT seconds of continuous
    silence following detected speech.

    Returns:
        numpy.ndarray or None: Recorded audio (float32, 16kHz, mono),
        or None if no speech was detected within INITIAL_TIMEOUT.
    """
    chunk_samples = int(SAMPLE_RATE * CHUNK_DURATION)
    audio_chunks = []
    silence_duration = 0.0
    speech_detected = False
    total_duration = 0.0

    print("[Audio] Recording started... Speak now!")

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32") as stream:
        while True:
            data, overflowed = stream.read(chunk_samples)
            if overflowed:
                print("[Audio] Warning: Buffer overflow")

            audio_chunks.append(data.copy())
            total_duration += CHUNK_DURATION

            # Calculate RMS energy
            rms = np.sqrt(np.mean(data ** 2))

            if rms >= SILENCE_THRESHOLD:
                speech_detected = True
                silence_duration = 0.0
            else:
                silence_duration += CHUNK_DURATION

            # No speech within timeout
            if not speech_detected and total_duration >= INITIAL_TIMEOUT:
                print("\n[Audio] No speech detected (timeout).")
                return None

            # Silence after speech → done recording
            if speech_detected and silence_duration >= SILENCE_TIMEOUT:
                print(f"\n[Audio] Silence detected. Recorded {total_duration:.1f}s.")
                break

            # Safety limit
            if total_duration >= MAX_RECORD_DURATION:
                print(f"\n[Audio] Max duration reached ({MAX_RECORD_DURATION}s).")
                break

    return np.concatenate(audio_chunks, axis=0)


def save_to_wav(audio_data):
    """
    Save a float32 audio array to a temporary WAV file.

    Args:
        audio_data: numpy array of float32 audio samples.

    Returns:
        str: Path to the temporary WAV file.
    """
    tmp_path = os.path.join(tempfile.gettempdir(), "stt_recording.wav")
    audio_int16 = (audio_data * 32767).astype(np.int16)

    with wave.open(tmp_path, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_int16.tobytes())

    return tmp_path


# ─────────────────────────────────────────────────────────────────────────────
# STT Processing
# ─────────────────────────────────────────────────────────────────────────────

def stt_worker():
    """Background worker: records audio and transcribes with Faster-Whisper."""
    global recording_active, is_listening

    while True:
        task = audio_queue.get(block=True)
        if task != "LISTEN":
            continue

        recording_active = True
        ui_queue.put(("SHOW", LANGUAGES[current_lang_idx][2]))

        # Record audio
        audio_data = None
        try:
            audio_data = record_until_silence()
        except Exception as e:
            print(f"[STT] Microphone error: {e}")

        ui_queue.put(("HIDE", ""))
        is_listening = False

        # Transcribe if we got audio
        if audio_data is not None and len(audio_data) > 0:
            lang_code = LANGUAGES[current_lang_idx][1]
            print(f"[STT] Transcribing ({lang_code})...")

            try:
                wav_path = save_to_wav(audio_data)
                initial_prompt = ARABIC_PROMPT if lang_code == "ar" else None

                segments, _ = whisper_model.transcribe(
                    wav_path,
                    language=lang_code,
                    beam_size=1,
                    vad_filter=True,
                    vad_parameters={"min_silence_duration_ms": 2000},
                    initial_prompt=initial_prompt,
                    condition_on_previous_text=False,
                )

                text = " ".join(seg.text.strip() for seg in segments).strip()

                if text:
                    print(f"[STT] Result: {text}")
                    pyperclip.copy(text + " ")
                    keyboard.send("ctrl+v")
                else:
                    print("[STT] No text recognized.")

                # Cleanup temp file
                try:
                    os.remove(wav_path)
                except OSError:
                    pass

            except Exception as e:
                print(f"[STT] Transcription error: {e}")

        recording_active = False


# ─────────────────────────────────────────────────────────────────────────────
# Hotkey Callbacks
# ─────────────────────────────────────────────────────────────────────────────

def on_record():
    """F9 hotkey: start recording."""
    global is_listening

    if not model_loaded:
        print("[App] Model still loading, please wait...")
        return

    if not is_listening and not recording_active:
        is_listening = True
        audio_queue.put("LISTEN")


def on_switch_language():
    """F10 hotkey: toggle between languages."""
    global current_lang_idx

    if is_listening or recording_active:
        print("[App] Cannot switch language while recording.")
        return

    current_lang_idx = (current_lang_idx + 1) % len(LANGUAGES)
    lang_name, _, lang_abbr = LANGUAGES[current_lang_idx]
    print(f"[App] Language: {lang_name}")
    ui_queue.put(("FLASH", lang_abbr))


# ─────────────────────────────────────────────────────────────────────────────
# UI (Tkinter)
# ─────────────────────────────────────────────────────────────────────────────

def create_supersampled_pill(w, h, r, color, scale=4):
    """Create an anti-aliased rounded rectangle image."""
    img = Image.new("RGBA", (w * scale, h * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        (2 * scale, 2 * scale, (w - 2) * scale, (h - 2) * scale),
        radius=r * scale, fill=color,
    )
    return img.resize((w, h), Image.Resampling.LANCZOS)


def create_supersampled_circle(size, color, scale=4):
    """Create an anti-aliased circle image."""
    img = Image.new("RGBA", (size * scale, size * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((0, 0, size * scale, size * scale), fill=color)
    return img.resize((size, size), Image.Resampling.LANCZOS)


def start_ui():
    """Main thread: floating pill UI with waveform animation."""
    import tkinter as tk

    root = tk.Tk()
    root.title("STT Service")
    root.overrideredirect(True)
    root.attributes("-topmost", True)

    transparent_color = "gray"
    root.config(bg=transparent_color)
    try:
        root.attributes("-transparentcolor", transparent_color)
    except Exception:
        pass

    # Center bottom of screen
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    win_w, win_h = 240, 60
    root.geometry(f"{win_w}x{win_h}+{(screen_w - win_w) // 2}+{screen_h - 150}")

    canvas = tk.Canvas(root, width=win_w, height=win_h, bg=transparent_color, highlightthickness=0)
    canvas.pack()

    from PIL import ImageTk

    # Pre-render UI assets
    bg_photo = ImageTk.PhotoImage(create_supersampled_pill(win_w, win_h, 28, THEME_BG))
    logo_green = ImageTk.PhotoImage(create_supersampled_circle(44, COLOR_GREEN))
    logo_blue = ImageTk.PhotoImage(create_supersampled_circle(44, COLOR_BLUE))
    logo_orange = ImageTk.PhotoImage(create_supersampled_circle(44, COLOR_ORANGE))

    canvas.create_image(0, 0, image=bg_photo, anchor="nw")
    icon_bg = canvas.create_image(8, 8, image=logo_green, anchor="nw")
    label = canvas.create_text(30, 30, text="EN", fill="black", font=("Segoe UI", 12, "bold"))
    loading_label = canvas.create_text(140, 30, text="", fill=COLOR_ORANGE, font=("Segoe UI", 10, "bold"))

    # Waveform bars
    bars = []
    for i in range(20):
        bar = canvas.create_line(
            75 + i * 7, 30, 75 + i * 7, 30,
            fill="gray", width=4, capstyle=tk.ROUND, joinstyle=tk.ROUND,
        )
        bars.append(bar)

    root.withdraw()
    time_step = [0.0]
    loading_active = [False]

    # ── Animations ──

    def animate_loading():
        if not loading_active[0]:
            return
        time_step[0] += 0.15
        for i, bar in enumerate(bars):
            h = (math.sin(time_step[0] * 2 - i * 0.35) * 0.5 + 0.5) * 12 + 2
            cx = canvas.coords(bar)[0]
            canvas.coords(bar, cx, 30 - h, cx, 30 + h)
        dots = "." * (int(time_step[0] * 2) % 4)
        canvas.itemconfig(loading_label, text=f"Loading AI{dots}")
        root.after(50, animate_loading)

    def animate_wave():
        if not is_listening:
            return
        time_step[0] += 0.4
        for i, bar in enumerate(bars):
            h = abs(math.sin(time_step[0] + i * 0.5) * 8) + random.uniform(0, 6) + 2
            cx = canvas.coords(bar)[0]
            canvas.coords(bar, cx, 30 - h, cx, 30 + h)
        root.after(40, animate_wave)

    def set_wave_color(color):
        for bar in bars:
            canvas.itemconfig(bar, fill=color)

    def flatten_bars():
        for bar in bars:
            cx = canvas.coords(bar)[0]
            canvas.coords(bar, cx, 28, cx, 32)

    def set_icon(mode):
        icons = {"green": logo_green, "blue": logo_blue, "orange": logo_orange}
        canvas.itemconfig(icon_bg, image=icons.get(mode, logo_green))

    # ── Queue Handler ──

    def check_queue():
        try:
            while True:
                msg, val = ui_queue.get_nowait()

                if msg == "LOADING_START":
                    loading_active[0] = True
                    canvas.itemconfig(label, text="⏳")
                    set_icon("orange")
                    set_wave_color(COLOR_ORANGE)
                    root.deiconify()
                    animate_loading()

                elif msg == "LOADING_DONE":
                    loading_active[0] = False
                    canvas.itemconfig(label, text="✓")
                    canvas.itemconfig(loading_label, text="Ready!")
                    set_icon("green")
                    set_wave_color(COLOR_GREEN)
                    flatten_bars()
                    root.after(2000, lambda: root.withdraw() if not is_listening else None)

                elif msg == "LOADING_FAIL":
                    loading_active[0] = False
                    canvas.itemconfig(label, text="✗")
                    canvas.itemconfig(loading_label, text="Error!")
                    set_wave_color(COLOR_RED)
                    root.after(5000, root.withdraw)

                elif msg == "SHOW":
                    canvas.itemconfig(label, text=val)
                    canvas.itemconfig(loading_label, text="")
                    set_icon("green")
                    set_wave_color(COLOR_GREEN)
                    root.deiconify()
                    animate_wave()

                elif msg == "HIDE":
                    root.withdraw()

                elif msg == "FLASH":
                    canvas.itemconfig(label, text=val)
                    canvas.itemconfig(loading_label, text="")
                    flatten_bars()
                    set_wave_color(COLOR_BLUE)
                    set_icon("blue")
                    root.deiconify()
                    root.after(1500, lambda: root.withdraw() if not is_listening else None)

        except queue.Empty:
            pass

        root.after(100, check_queue)

    root.after(100, check_queue)
    root.mainloop()


# ─────────────────────────────────────────────────────────────────────────────
# System Tray
# ─────────────────────────────────────────────────────────────────────────────

def create_tray_icon():
    """Draw a microphone icon for the system tray."""
    scale = 4
    img = Image.new("RGBA", (64 * scale, 64 * scale), (0, 0, 0, 0))
    dc = ImageDraw.Draw(img)

    dc.rounded_rectangle((24 * scale, 8 * scale, 40 * scale, 36 * scale),
                          radius=8 * scale, fill=COLOR_GREEN)
    dc.arc((16 * scale, 20 * scale, 48 * scale, 52 * scale),
           start=0, end=180, fill="#ffffff", width=4 * scale)
    dc.line((32 * scale, 52 * scale, 32 * scale, 60 * scale), fill="#ffffff", width=4 * scale)
    dc.line((20 * scale, 60 * scale, 44 * scale, 60 * scale), fill="#ffffff", width=4 * scale)

    return img.resize((64, 64), Image.Resampling.LANCZOS)


def setup_tray():
    """Run the system tray icon."""
    def on_quit(icon, _):
        icon.stop()
        print("\n[App] Exiting from tray...")
        os._exit(0)

    icon = pystray.Icon(
        "STT",
        create_tray_icon(),
        "Speech-to-Text Service (Offline)",
        pystray.Menu(pystray.MenuItem("Exit STT Service", on_quit)),
    )
    icon.run()


# ─────────────────────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    """Start the Speech-to-Text service."""
    print("=" * 50)
    print("  Speech-to-Text Service (Faster-Whisper / Offline)")
    print("=" * 50)
    print("Shortcuts:")
    print("  F9  : Start Recording")
    print("  F10 : Toggle Language (EN/AR)")
    print("\nRunning in background. Press Ctrl+C to exit.\n")

    # Background threads
    threading.Thread(target=load_model, daemon=True).start()
    threading.Thread(target=stt_worker, daemon=True).start()
    threading.Thread(target=setup_tray, daemon=True).start()

    # Global hotkeys
    try:
        keyboard.add_hotkey("f9", on_record, suppress=True)
        keyboard.add_hotkey("f10", on_switch_language, suppress=True)
    except Exception as e:
        print(f"[Error] Failed to register hotkeys: {e}")
        sys.exit(1)

    # UI must run on the main thread
    try:
        start_ui()
    except KeyboardInterrupt:
        print("\n[App] Exiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
