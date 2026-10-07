# logic/system_tools.py
import os
import sys
import json
import re
import base64
import shutil
import subprocess
import winreg
import webbrowser
import socket
import ctypes
from ctypes import wintypes

from config import (
    CF_UNICODETEXT,
    CREATE_NO_WINDOW,
    DEFAULT_SELECTED,
    SECRET_CREDENTIAL_KEYS,
    WINGET_QUERY_TIMEOUT,
    APP_NAME,
    APP_VERSION,
    REPO_URL,
)

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
crypt32 = ctypes.windll.crypt32

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


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def prevent_sleep():
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000002 | 0x00000001)


def allow_sleep():
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def get_usb_directory():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_vault_path(usb_dir):
    return os.path.join(usb_dir, "devkit_vault.json")


def empty_vault():
    return {
        "selected_apps": list(DEFAULT_SELECTED),
        "custom_apps": [],
        "credentials": {
            "google_email": "",
            "github_token": "",
            "git_username": "",
            "docker_username": "",
            "docker_password": "",
        },
    }


def _dpapi_protect(plain: str) -> str:
    if not plain:
        return ""
    raw = plain.encode("utf-8")
    buffer = ctypes.create_string_buffer(raw)
    in_blob = DATA_BLOB(len(raw), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    out_blob = DATA_BLOB()
    if not crypt32.CryptProtectData(
        ctypes.byref(in_blob), "DevKitEngine", None, None, None, 0, ctypes.byref(out_blob)
    ):
        return plain
    try:
        data = ctypes.string_at(out_blob.pbData, out_blob.cbData)
        return "dpapi:" + base64.b64encode(data).decode("ascii")
    finally:
        kernel32.LocalFree(out_blob.pbData)


def _dpapi_unprotect(token: str) -> str:
    if not token:
        return ""
    if not token.startswith("dpapi:"):
        return token
    try:
        raw = base64.b64decode(token[6:])
        buffer = ctypes.create_string_buffer(raw)
        in_blob = DATA_BLOB(len(raw), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
        out_blob = DATA_BLOB()
        if not crypt32.CryptUnprotectData(
            ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)
        ):
            return ""
        try:
            return ctypes.string_at(out_blob.pbData, out_blob.cbData).decode("utf-8")
        finally:
            kernel32.LocalFree(out_blob.pbData)
    except Exception:
        return ""


def _protect_credentials(creds: dict) -> dict:
    sealed = dict(creds)
    for key in SECRET_CREDENTIAL_KEYS:
        sealed[key] = _dpapi_protect(sealed.get(key, "") or "")
    return sealed


def _reveal_credentials(creds: dict) -> dict:
    revealed = dict(creds)
    for key in SECRET_CREDENTIAL_KEYS:
        revealed[key] = _dpapi_unprotect(revealed.get(key, "") or "")
    return revealed


def load_vault(usb_dir):
    vault_path = get_vault_path(usb_dir)
    if os.path.exists(vault_path):
        try:
            with open(vault_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = empty_vault()
            merged["selected_apps"] = data.get("selected_apps", merged["selected_apps"])
            merged["custom_apps"] = data.get("custom_apps", [])
            creds = merged["credentials"]
            creds.update(data.get("credentials", {}))
            merged["credentials"] = _reveal_credentials(creds)
            return merged
        except Exception:
            pass
    return empty_vault()


def save_vault(usb_dir, data):
    vault_path = get_vault_path(usb_dir)
    payload = {
        "selected_apps": list(data.get("selected_apps", [])),
        "custom_apps": list(data.get("custom_apps", [])),
        "credentials": _protect_credentials(dict(data.get("credentials", {}))),
    }
    try:
        with open(vault_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4)
        return True
    except Exception:
        return False


def run_hidden(command, timeout=None, input_text=None):
    kwargs = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "shell": True,
        "creationflags": CREATE_NO_WINDOW,
        "timeout": timeout,
    }
    if input_text is None:
        kwargs["stdin"] = subprocess.DEVNULL
        return subprocess.run(command, **kwargs)
    kwargs["input"] = input_text
    return subprocess.run(command, **kwargs)


def is_winget_available():
    return shutil.which("winget") is not None


def is_internet_available():
    for host in ("1.1.1.1", "8.8.8.8"):
        try:
            socket.create_connection((host, 53), timeout=2)
            return True
        except OSError:
            continue
    try:
        socket.create_connection(("www.microsoft.com", 443), timeout=3)
        return True
    except OSError:
        return False


def parse_winget_table(text):
    """Return list of row dicts from a winget list/search table."""
    lines = [line.rstrip() for line in (text or "").splitlines()]
    header_idx = None
    header = ""
    for i, line in enumerate(lines):
        if re.search(r"\bName\b", line) and re.search(r"\bId\b", line):
            header_idx = i
            header = line
            break
    if header_idx is None:
        return []

    id_start = header.find("Id")
    ver_start = header.find("Version")
    if id_start < 0:
        return []

    rows = []
    started = False
    for line in lines[header_idx + 1 :]:
        if not line.strip():
            continue
        if set(line.strip()) <= {"-"}:
            started = True
            continue
        if not started and id_start < len(line):
            started = True
        if not started:
            continue
        name = line[:id_start].strip()
        rest = line[id_start:]
        if ver_start > id_start:
            width = ver_start - id_start
            package_id = rest[:width].strip()
        else:
            package_id = rest.split()[0] if rest.split() else ""
        if package_id:
            rows.append({"name": name, "id": package_id})
    return rows


def parse_winget_ids(text):
    return {row["id"].lower() for row in parse_winget_table(text)}


def resolve_winget_id(raw_query):
    query = (raw_query or "").strip()
    if not query:
        return None
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.[A-Za-z0-9][A-Za-z0-9_.-]*", query):
        return query
    try:
        result = run_hidden(
            ["winget", "search", query, "--accept-source-agreements"],
            timeout=WINGET_QUERY_TIMEOUT,
        )
    except Exception:
        return None
    rows = parse_winget_table(result.stdout)
    if not rows:
        match = re.search(r"\b([A-Za-z0-9_.-]+\.[A-Za-z0-9_.-]+)\b", result.stdout or "")
        return match.group(1) if match else None
    q = query.lower()
    for row in rows:
        if row["id"].lower() == q or row["name"].lower() == q:
            return row["id"]
    for row in rows:
        if q in row["id"].lower() or q in row["name"].lower():
            return row["id"]
    return rows[0]["id"]


class InstallIndex:
    def __init__(self):
        self.ids = set()
        self.names = []
        self.ready = False

    def is_installed(self, app_display_name, winget_id):
        if winget_id and winget_id.lower() in self.ids:
            return True
        needle = (app_display_name or "").lower()
        if needle and any(needle in name for name in self.names):
            return True
        return False


def _registry_display_names():
    names = []
    paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    for hive, path in paths:
        try:
            with winreg.OpenKey(hive, path) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            val, _ = winreg.QueryValueEx(subkey, "DisplayName")
                            if val:
                                names.append(val.lower())
                    except OSError:
                        continue
        except OSError:
            continue
    return names


def build_install_index():
    index = InstallIndex()
    try:
        result = run_hidden(
            ["winget", "list", "--accept-source-agreements"],
            timeout=WINGET_QUERY_TIMEOUT,
        )
        index.ids = parse_winget_ids(result.stdout)
    except Exception:
        index.ids = set()
    try:
        index.names = _registry_display_names()
    except Exception:
        index.names = []
    index.ready = True
    return index


def is_app_installed(app_display_name, winget_id, index=None):
    if index is not None:
        return index.is_installed(app_display_name, winget_id)
    return build_install_index().is_installed(app_display_name, winget_id)


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


def find_chrome_path():
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def format_duration(seconds):
    seconds = max(0, int(seconds))
    minutes, rem = divmod(seconds, 60)
    if minutes:
        return f"{minutes}m {rem}s"
    return f"{rem}s"


def generate_and_open_success_html(usb_dir, summary=None):
    summary = summary or {}
    installed = summary.get("installed", [])
    skipped = summary.get("skipped", [])
    failed = summary.get("failed", [])
    elapsed = summary.get("elapsed", "—")
    overall = summary.get("status", "success")

    def _items(entries, empty):
        if not entries:
            return f'<li class="empty">{empty}</li>'
        return "".join(f"<li>{_escape(item)}</li>" for item in entries)

    title = "Deployment Successful" if overall == "success" else "Deployment Finished With Issues"
    badge = "SYSTEM READY" if overall == "success" else "REVIEW REQUIRED"
    accent = "#E11D48" if overall == "success" else "#FBBF24"

    html_path = os.path.join(usb_dir, "Setup_Complete.html")
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{APP_NAME} — Setup Complete</title>
    <style>
        :root {{ --accent: {accent}; }}
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0; min-height: 100vh; color: #F4F4F5;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background:
                radial-gradient(1200px 500px at 50% -10%, rgba(225,29,72,0.18), transparent 55%),
                #050505;
            display: flex; align-items: center; justify-content: center; padding: 32px 16px;
        }}
        .card {{
            width: min(720px, 100%); background: #111214; border: 1px solid #2A2D33;
            border-radius: 16px; padding: 40px 36px; box-shadow: 0 24px 80px rgba(0,0,0,0.55);
        }}
        .badge {{
            display: inline-block; padding: 6px 12px; border-radius: 999px;
            border: 1px solid #3F0D1C; background: #1A0A10; color: var(--accent);
            font-size: 11px; font-weight: 700; letter-spacing: 1.4px;
        }}
        h1 {{ margin: 16px 0 8px; font-size: 30px; letter-spacing: 0.3px; }}
        .lede {{ color: #A1A1AA; line-height: 1.6; margin: 0 0 24px; }}
        .meta {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 28px; }}
        .pill {{
            background: #181A1D; border: 1px solid #2A2D33; border-radius: 8px;
            padding: 10px 12px; min-width: 120px;
        }}
        .pill span {{ display: block; color: #71717A; font-size: 11px; letter-spacing: 0.8px; }}
        .pill strong {{ font-size: 18px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; }}
        h2 {{ font-size: 12px; letter-spacing: 1px; color: #A1A1AA; margin: 0 0 8px; }}
        ul {{ margin: 0; padding-left: 18px; color: #D4D4D8; font-size: 14px; line-height: 1.7; }}
        .empty {{ color: #71717A; list-style: none; margin-left: -18px; }}
        .footer {{
            border-top: 1px solid #2A2D33; margin-top: 28px; padding-top: 18px;
            color: #71717A; font-size: 13px;
        }}
        a {{ color: #E11D48; text-decoration: none; font-weight: 700; }}
        a:hover {{ color: #BE123C; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="badge">{badge}</div>
        <h1>{title}</h1>
        <p class="lede">{APP_NAME} {APP_VERSION} finished configuring this Windows machine from official WinGet packages. Credentials never left this device.</p>
        <div class="meta">
            <div class="pill"><span>INSTALLED</span><strong>{len(installed)}</strong></div>
            <div class="pill"><span>SKIPPED</span><strong>{len(skipped)}</strong></div>
            <div class="pill"><span>FAILED</span><strong>{len(failed)}</strong></div>
            <div class="pill"><span>ELAPSED</span><strong>{_escape(elapsed)}</strong></div>
        </div>
        <div class="grid">
            <div><h2>INSTALLED</h2><ul>{_items(installed, "Nothing new to install")}</ul></div>
            <div><h2>ALREADY PRESENT</h2><ul>{_items(skipped, "No skips")}</ul></div>
            <div><h2>NEEDS ATTENTION</h2><ul>{_items(failed, "No failures")}</ul></div>
        </div>
        <div class="footer">
            Engineered by <a href="{REPO_URL}" target="_blank">Faisal Adnan & Team</a><br>
            <span style="font-size: 12px; margin-top: 6px; display: block;">Local automation core · WinGet · Zero telemetry</span>
        </div>
    </div>
</body>
</html>"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    webbrowser.open(f"file:///{html_path.replace(os.sep, '/')}")


def _escape(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
