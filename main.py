# main.py
import sys
import ctypes


# --- FORCE ADMIN PRIVILEGES ON START ---
def run_as_admin():
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        is_admin = False

    if not is_admin:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit()


# ── FIX: Tell Windows taskbar this is its own app, not python.exe ──────────
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
    "Faisal6951.DevKitEngine.Apex.1"
)

# ── FIX: DPI blur on scaled displays ────────────────────────────────────────
# Without this, Windows stretches small icon sizes on 125%/150%/200% displays.
# SetProcessDpiAwareness(2) = per-monitor aware — uses correct size from the ICO.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()  # fallback for older Windows
    except Exception:
        pass

if __name__ == "__main__":
    run_as_admin()

    # Safe import only after administrative check passes
    from ui.launcher_ui import DevKitLauncher

    app = DevKitLauncher()
    app.mainloop()
