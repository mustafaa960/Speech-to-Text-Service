# 🎙️ Speech-to-Text Service

A lightweight, **offline** background speech-to-text service for Windows. Press a hotkey, speak, and your words are instantly typed into any active window.

Powered by [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) — runs **100% locally** with no internet required.

---

## ✨ Features

| Feature                        | Description                                                                |
| ------------------------------ | -------------------------------------------------------------------------- |
| 🎤 **Offline STT**             | Uses Faster-Whisper (OpenAI Whisper reimplementation) — no internet needed |
| 🌐 **Multi-Language**          | English & Arabic (Iraqi dialect) with hotkey switching                     |
| ⚡ **Fast**                    | Up to 4x faster than OpenAI Whisper with INT8 quantization on CPU          |
| 🎨 **Sleek UI**                | Floating pill-shaped indicator with animated waveform                      |
| 🔇 **Smart Silence Detection** | Automatically stops recording after you finish speaking                    |
| ⏳ **Loading Animation**       | Pulsing orange animation while the AI model loads                          |
| 🖥️ **System Tray**             | Runs quietly in the background with a tray icon                            |
| 🔒 **Privacy**                 | All processing happens on your machine — audio never leaves your device    |

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Windows 10/11**

### Installation

```bash
# Clone the repository
git clone https://github.com/mustafaa960/Speech-to-Text-Service.git
cd Speech-to-Text-Service

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run

```bash
python speech_to_text.py
```

> **First run** will automatically download the Whisper `medium` model (~1.5GB). After that, it works fully offline.

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action                             |
| -------- | ---------------------------------- |
| `F9`     | Start/stop recording               |
| `F10`    | Toggle language (English ↔ Arabic) |

---

## 🎯 How It Works

```
Press F9 → 🎤 Microphone records your voice
         → 🔇 Silence detected → stops recording
         → 🧠 Faster-Whisper transcribes locally
         → 📋 Text copied to clipboard
         → ⌨️ Auto-pasted into active window
```

### UI States

| State               | Appearance                                        |
| ------------------- | ------------------------------------------------- |
| **Loading**         | 🟠 Orange pulsing wave — "Loading AI..."          |
| **Ready**           | 🟢 Green flash — "✓ Ready!" (auto-hides)          |
| **Listening**       | 🟢 Green dancing waveform with language indicator |
| **Language Switch** | 🔵 Blue flash with new language code              |

---

## 🏗️ Build Windows Executable

To build a standalone `.exe` that runs without Python:

```bash
pip install pyinstaller
python -m PyInstaller STT-Service-v7.spec --clean
```

The executable will be created at `dist/STT-Service-v7.exe`.

---

## 🍎 Mac Compatibility (Work in Progress)

Currently, the application is optimized for **Windows**. To run it on macOS or make it fully cross-platform, the following modifications are required:

- **Hotkeys**: Replace the Windows-specific `keyboard` library with a cross-platform equivalent like `pynput` (requires Accessibility permissions on Mac).
- **Clipboard/Paste**: Update the auto-paste shortcut from `Ctrl+V` to `Command+V` (`⌘+V`).
- **GPU Acceleration**: NVIDIA CUDA is not available on Apple Silicon (M1/M2/M3). The application will automatically fall back to CPU execution, which is fully supported but slower.
- **UI Translucency**: The Windows-only `-transparentcolor` Tkinter attribute must be bypassed or replaced with a Mac-friendly alternative.
- **Bundling**: Build a `.app` bundle using PyInstaller instead of an `.exe`.

---

## 📁 Project Structure

```
Speech-to-Text-Service/
├── speech_to_text.py      # Main application
├── requirements.txt       # Python dependencies
├── STT-Service-v7.spec    # PyInstaller build config
├── .gitignore
└── README.md
```

---

## 🛠️ Configuration

Key parameters in `speech_to_text.py` that you can tune:

| Parameter             | Default  | Description                                                   |
| --------------------- | -------- | ------------------------------------------------------------- |
| `SILENCE_THRESHOLD`   | `0.003`  | RMS energy below this = silence                               |
| `SILENCE_TIMEOUT`     | `3.5s`   | Seconds of silence before stopping                            |
| `MAX_RECORD_DURATION` | `120s`   | Maximum recording length                                      |
| `INITIAL_TIMEOUT`     | `15s`    | Timeout if no speech detected                                 |
| Model size            | `medium` | Whisper model (`tiny`, `base`, `small`, `medium`, `large-v3`) |

---

## 📦 Dependencies

| Package          | Purpose                       |
| ---------------- | ----------------------------- |
| `faster-whisper` | Offline speech-to-text engine |
| `sounddevice`    | Microphone audio recording    |
| `numpy`          | Audio buffer management       |
| `keyboard`       | Global hotkey registration    |
| `pyperclip`      | Clipboard operations          |
| `pystray`        | System tray icon              |
| `Pillow`         | UI graphics rendering         |

---

## 🗺️ Roadmap

Future enhancements planned using additional AI technologies:

- [ ] **Voice Response (TTS)** — XTTS-v2 for spoken feedback in Arabic/English
- [ ] **Smart Voice Commands** — all-MiniLM-L6-v2 for semantic command understanding
- [ ] **Voice Cloning** — OpenVoice for personalized voice output
- [x] **GPU Acceleration** — CUDA support for faster transcription (Windows/NVIDIA)
- [ ] **Cross-Platform Support** — Full compatibility for macOS & Linux

---

## 📄 License

MIT License — free for personal and commercial use.
