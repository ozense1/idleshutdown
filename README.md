# 📴 Idle Shutdown Application

**Idle Shutdown** is Windows system tray application that automatically shuts down your computer after the set idle period. Features include pause/resume control, adjustable idle timeout, logging, and a minute warning prompt before shutdown. Built with pystray and tkinter.

## Features

- Auto-shutdown after a configurable idle time  
- Pause/resume monitoring from the tray menu  
- Set idle threshold in seconds  
- View real-time activity log via GUI  
- Saves daily logs (auto-cleans after 60 days)  
- 60-second shutdown warning with cancel option  

## Installation

1. Download **`IdleShutdownSetup.exe`** from the [Releases](https://github.com/your-username/your-repo/releases) 
2. Run the installer and follow the prompts.

## 🛠 Build from Source

**Requirements:** `pystray`, `Pillow`, `tkinter` (comes with Python)

To build using PyInstaller:

```bash
pyinstaller --noconfirm --onefile --windowed --icon=shutdown_icon.ico idle_shutdown_tray_app.py
```

## Disclaimer
This application was created primarily for personal use. While it's shared publicly in case others find it useful, it comes without any guarantees. Use at your own discretion.