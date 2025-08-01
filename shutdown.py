import time
import glob
import threading
import ctypes
import sys
import os
from datetime import datetime
from pystray import Icon, Menu, MenuItem
from PIL import Image
import tkinter as tk
from tkinter import simpledialog
import queue
import subprocess


ui_queue = queue.Queue()
log = []

def log_event(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry)
    log.append(entry)

    # Save to daily log file
    if hasattr(sys, '_MEIPASS'):
        exe_dir = os.path.dirname(sys.executable)
    else:
        exe_dir = os.path.dirname(__file__)
    log_dir = os.path.join(exe_dir, "logs")

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_filename = os.path.join(log_dir, datetime.now().strftime("log_%Y-%m-%d.txt"))

    with open(log_filename, "a", encoding="utf-8") as f:
        f.write(entry + "\n")

def cleanup_old_logs():
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    if not os.path.exists(log_dir):
        return
    now = datetime.now()
    for log_file in glob.glob(os.path.join(log_dir, "log_*.txt")):
        # Extract date from filename
        basename = os.path.basename(log_file)
        try:
            date_str = basename[4:-4]  # 'log_YYYY-MM-DD.txt' -> 'YYYY-MM-DD'
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            if (now - file_date).days > 60:
                os.remove(log_file)
        except Exception:
            pass

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(__file__), relative_path)

def get_idle_duration():
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        return millis / 1000.0
    return 0

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

class IdleShutdownTrayApp:
    def __init__(self):
        cleanup_old_logs()
        self.is_paused = False
        self.shutdown_timer = None
        self.shutdown_warning_displayed = False
        self.idle_threshold = 3600  # default 1 hour
        self.log_window = None
        icon_path = resource_path("shutdown_icon.ico")
        self.icon = self.create_icon(icon_path)
        self.monitor_thread = threading.Thread(target=self.check_idle_time, daemon=True)
        self.monitor_thread.start()
        self.ui_processor_thread = threading.Thread(target=self.process_global_queue, daemon=True)
        self.ui_processor_thread.start()

    def process_global_queue(self):
        while True:
            try:
                task = ui_queue.get_nowait()
                task()
            except queue.Empty:
                time.sleep(0.1)

    def create_icon(self, icon_path):
        image = Image.open(icon_path)

        menu = Menu(
            MenuItem('Pause', self.toggle_pause, checked=lambda item: self.is_paused),
            MenuItem('Set Idle Limit', self.set_idle_time),
            MenuItem('Log', self.show_log),
            MenuItem('Quit', self.quit_app)
        )
        return Icon("IdleShutdown", image, "Idle Shutdown", menu)

    def toggle_pause(self, icon, item):
        self.is_paused = not self.is_paused
        log_event("Paused" if self.is_paused else "Resumed")
        icon.update_menu()

    def set_idle_time(self):
        def ask_idle_threshold():
            root = tk.Tk()
            root.withdraw()
            result = simpledialog.askinteger("Set Idle Limit", "Enter idle time in seconds:", minvalue=5, parent=root)
            if result:
                self.idle_threshold = result
                log_event(f"Idle threshold set to {result} seconds.")
            root.destroy()

        ui_queue.put(ask_idle_threshold)


    def show_log(self):
        if self.log_window and self.log_window.winfo_exists():
            self.log_window.lift()
            return

        def run():
            self.log_window = tk.Tk()
            self.log_window.title("Idle Shutdown Log")
            icon_path = resource_path("shutdown_icon.ico")
            self.log_window.iconbitmap(icon_path)
            self.log_window.geometry("700x400")
            self.log_window.minsize(500, 300)

            text = tk.Text(self.log_window, wrap=tk.WORD)
            text.pack(fill="both", expand=True, padx=10, pady=10)
            text.config(state=tk.DISABLED)

            def update_log():
                if not self.log_window.winfo_exists():
                    return
                text.config(state=tk.NORMAL)
                text.delete(1.0, tk.END)
                text.insert(tk.END, "\n".join(log))
                text.config(state=tk.DISABLED)
                self.log_window.after(1000, update_log)

            def process_ui_queue():
                try:
                    while True:
                        task = ui_queue.get_nowait()
                        task()
                except queue.Empty:
                    pass
                if self.log_window:
                    self.log_window.after(100, process_ui_queue)

            update_log()
            process_ui_queue()
            self.log_window.protocol("WM_DELETE_WINDOW", self.window_close)
            self.log_window.mainloop()

        threading.Thread(target=run).start()

    def window_close(self):
        if self.log_window:
            self.log_window.destroy()
            self.log_window = None

    def quit_app(self):
        log_event("Application terminated by user.")
        self.icon.stop()
        os._exit(0)

    def check_idle_time(self):
        while True:
            if not self.is_paused:
                idle_time = get_idle_duration()
                if idle_time >= self.idle_threshold and not self.shutdown_warning_displayed:
                    self.shutdown_warning_displayed = True
                    log_event(f"Idle for {self.idle_threshold} seconds. Showing shutdown warning.")
                    self.shutdown_window()
            time.sleep(5)

    def shutdown_window(self):
        def prompt():
            log_event("Issuing shutdown command.")

            def do_shutdown():
                subprocess.run([r"C:\\Windows\\System32\\shutdown.exe", "/s", "/t", "60"])
            threading.Thread(target=do_shutdown, daemon=True).start()

            def cancel_shutdown():
                log_event("Shutdown canceled by user.")
                subprocess.run([r"C:\\Windows\\System32\\shutdown.exe", "/a"])
                self.shutdown_warning_displayed = False
                root.destroy()

            root = tk.Tk()
            root.title("Idle Shutdown Warning")
            icon_path = resource_path("shutdown_icon.ico")
            root.iconbitmap(icon_path)
            window_width = 300
            window_height = 80
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            x = (screen_width // 2) - (window_width // 2)
            y = (screen_height // 2) - (window_height // 2) - 50
            root.geometry(f"{window_width}x{window_height}+{x}+{y}")
            root.resizable(False, False)
            root.attributes("-topmost", True)
            root.lift()
            root.focus_force()
            tk.Label(root, text="Computer idle. Shutdown in 1 minute.", wraplength=280).pack(pady=5)
            tk.Button(root, text="Cancel Shutdown", command=cancel_shutdown).pack(pady=5)
            root.mainloop()

        threading.Thread(target=prompt).start()

    def run(self):
        log_event("Application started.")
        self.icon.run()

if __name__ == "__main__":
    app = IdleShutdownTrayApp()
    app.run()
