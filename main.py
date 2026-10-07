# main.py
import os
import sys
import ctypes

from config import APP_ID


def run_as_admin():
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        is_admin = False

    if is_admin:
        return

    if getattr(sys, "frozen", False):
        executable = sys.executable
        params = subprocess_join(sys.argv[1:])
    else:
        executable = sys.executable
        script = os.path.abspath(sys.argv[0])
        params = subprocess_join([script, *sys.argv[1:]])

    ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, params, None, 1)
    sys.exit()


def subprocess_join(args):
    parts = []
    for arg in args:
        if not arg:
            continue
        if any(ch in arg for ch in ' \t"'):
            parts.append('"' + arg.replace('"', '\\"') + '"')
        else:
            parts.append(arg)
    return " ".join(parts)


run_as_admin()

ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


if __name__ == "__main__":
    from ui.launcher_ui import DevKitLauncher

    app = DevKitLauncher()
    app.mainloop()
