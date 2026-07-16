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

if __name__ == "__main__":
    run_as_admin()
    
    # Safe import only after administrative check passes
    from ui.launcher_ui import DevKitLauncher
    app = DevKitLauncher()
    app.mainloop()