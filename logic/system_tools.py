# logic/system_tools.py
import os
import sys
import json
import shutil
import subprocess
import winreg
import webbrowser
import socket
import ctypes
from ctypes import wintypes
from config import CF_UNICODETEXT

# Windows Native Clipboard Memory Management Setup
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.CloseClipboard.restype = wintypes.BOOL
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardData.restype = wintypes.HANDLE
user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
user32.IsClipboardFormatAvailable.restype = wintypes.BOOL

kernel32.GlobalLock.argtypes = [wintypes.HANDLE]
kernel32.GlobalLock.restype = wintypes.LPVOID
kernel32.GlobalUnlock.argtypes = [wintypes.HANDLE]
kernel32.GlobalUnlock.restype = wintypes.BOOL

def prevent_sleep():
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000002 | 0x00000001)

def allow_sleep():
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)

def get_usb_directory():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    # Move up 2 levels because this runs inside '/logic/system_tools.py'
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_vault_path(usb_dir):
    return os.path.join(usb_dir, "devkit_vault.json")

def load_vault(usb_dir):
    vault_path = get_vault_path(usb_dir)
    if os.path.exists(vault_path):
        try:
            with open(vault_path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "selected_apps": ["chrome", "git_bash", "vscode", "cursor"],
        "custom_apps": [],
        "credentials": {
            "google_email": "",
            "github_token": "",
            "git_username": "",
            "docker_username": "",
            "docker_password": ""
        }
    }

def save_vault(usb_dir, data):
    vault_path = get_vault_path(usb_dir)
    try:
        with open(vault_path, "w") as f:
            json.dump(data, f, indent=4)
        return True
    except Exception:
        return False

def is_winget_available():
    return shutil.which("winget") is not None

def is_internet_available():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False

def is_app_installed(app_display_name, winget_id):
    # LAYER 1: WinGet Check
    try:
        cmd = ["winget", "list", "--id", winget_id, "--exact"]
        result = subprocess.run(cmd, capture_output=True, text=True, creationflags=0x08000000)
        if result.returncode == 0:
            return True
    except:
        pass

    # LAYER 2: Registry Check
    registry_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall")
    ]
    for hive, path in registry_paths:
        try:
            with winreg.OpenKey(hive, path) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            val, _ = winreg.QueryValueEx(subkey, "DisplayName")
                            if app_display_name.lower() in val.lower():
                                return True
                    except: continue
        except: continue
    return False

def get_clipboard_text():
    if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
        return None
    if not user32.OpenClipboard(None):
        return None
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return None
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return None
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(handle)
    except Exception:
        return None
    finally:
        user32.CloseClipboard()

def generate_and_open_success_html(usb_dir):
    html_path = os.path.join(usb_dir, "Setup_Complete.html")
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dev-Kit Setup Complete</title>
    <style>
        body { background-color: #050505; color: #FFFFFF; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .container { background-color: #121212; border: 1px solid #262626; border-radius: 8px; padding: 50px 40px; text-align: center; max-width: 500px; box-shadow: 0 10px 30px rgba(0,0,0,0.8); }
        h1 { color: #E11D48; margin-bottom: 10px; font-size: 28px; letter-spacing: 1px; }
        p { color: #A3A3A3; line-height: 1.6; font-size: 15px; margin-bottom: 30px; }
        .badge { display: inline-block; padding: 8px 16px; background-color: #1A1A1A; border: 1px solid #404040; border-radius: 4px; color: #E11D48; font-weight: bold; font-size: 12px; letter-spacing: 1px; margin-bottom: 20px; }
        .footer { border-top: 1px solid #262626; margin-top: 20px; padding-top: 20px; font-size: 13px; color: #737373; }
        a { color: #E11D48; text-decoration: none; font-weight: bold; transition: color 0.2s; }
        a:hover { color: #BE123C; }
    </style>
</head>
<body>
    <div class="container">
        <div class="badge">SYSTEM READY</div>
        <h1>Deployment Successful</h1>
        <p>All selected applications, credentials, and automated workflows have been seamlessly installed and configured on your machine.</p>
        <p>You can now safely close the installer engine.</p>
        <div class="footer">
            Engineered by <a href="#" target="_blank">Faisal Adnan & Team</a><br>
            <span style="font-size: 11px; margin-top: 5px; display: block;">Frontend Development & Automation Core</span>
        </div>
    </div>
</body>
</html>"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    webbrowser.open(f"file:///{html_path.replace('\\', '/')}")