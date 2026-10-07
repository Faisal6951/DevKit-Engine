# logic/auth_tools.py
import os
import time
import subprocess

from config import CREATE_NO_WINDOW
from logic.system_tools import find_chrome_path, get_usb_directory


def authenticate_app(app_key, vault_data, logger_func, cancel_event=None):
    creds = vault_data.get("credentials", {})
    if app_key == "git_bash":
        _configure_git(creds, logger_func)
    elif app_key == "docker":
        _configure_docker(creds, logger_func, cancel_event)
    elif app_key == "chrome":
        _prepare_chrome_signin(creds, logger_func)


def _cancelled(cancel_event):
    return cancel_event is not None and cancel_event.is_set()


def _configure_git(creds, logger_func):
    user = (creds.get("git_username") or "").strip()
    token = (creds.get("github_token") or "").strip()
    email = (creds.get("google_email") or "").strip()
    if not user and not token and not email:
        return

    logger_func("[AUTOMATION] Writing local Git identity...")
    try:
        flags = CREATE_NO_WINDOW
        if user:
            subprocess.run(
                ["git", "config", "--global", "user.name", user],
                check=True,
                shell=True,
                creationflags=flags,
            )
        git_email = email or (f"{user}@users.noreply.github.com" if user else "")
        if git_email:
            subprocess.run(
                ["git", "config", "--global", "user.email", git_email],
                check=True,
                shell=True,
                creationflags=flags,
            )
        if user and token:
            subprocess.run(
                ["git", "config", "--global", "credential.helper", "store"],
                check=True,
                shell=True,
                creationflags=flags,
            )
            user_profile = os.environ.get("USERPROFILE", "C:\\Users\\Default")
            cred_path = os.path.join(user_profile, ".git-credentials")
            new_line = f"https://{user}:{token}@github.com"
            existing_lines = []
            if os.path.exists(cred_path):
                with open(cred_path, "r", encoding="utf-8", errors="replace") as f:
                    existing_lines = [line.strip() for line in f if line.strip()]
            kept = [line for line in existing_lines if "github.com" not in line.lower()]
            kept.append(new_line)
            with open(cred_path, "w", encoding="utf-8") as f:
                f.write("\n".join(kept) + "\n")
        logger_func("[SUCCESS] Git credentials mapped.")
    except Exception as e:
        logger_func(f"[ERROR] Git setup failed: {e}")


def _configure_docker(creds, logger_func, cancel_event):
    user = (creds.get("docker_username") or "").strip()
    password = (creds.get("docker_password") or "").strip()
    if not user or not password:
        return

    logger_func("[AUTOMATION] Waiting for Docker engine...")
    try:
        subprocess.Popen("start docker-desktop://", shell=True)
        last_err = ""
        for _ in range(12):
            if _cancelled(cancel_event):
                logger_func("[WARN] Docker login skipped — deployment cancelled.")
                return
            process = subprocess.Popen(
                ["docker", "login", "-u", user, "--password-stdin"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True,
                creationflags=CREATE_NO_WINDOW,
            )
            stdout, stderr = process.communicate(input=password)
            if process.returncode == 0:
                logger_func("[SUCCESS] Docker automation completed.")
                return
            last_err = (stderr or stdout or "").strip()
            time.sleep(5)
        logger_func(f"[ERROR] Docker login did not complete: {last_err or 'engine not ready'}")
    except Exception as e:
        logger_func(f"[ERROR] Docker login failed: {e}")


def _prepare_chrome_signin(creds, logger_func):
    email = (creds.get("google_email") or "").strip()
    if not email:
        return
    chrome = find_chrome_path()
    if not chrome:
        logger_func("[WARN] Chrome sign-in skipped — chrome.exe not found yet.")
        return
    profile_dir = os.path.join(get_usb_directory(), "DevKit", "profiles", "ChromeProfile")
    os.makedirs(profile_dir, exist_ok=True)
    login_url = f"https://accounts.google.com/ServiceLogin?Email={email}"
    logger_func("[AUTOMATION] Opening Chrome with your Google account hint...")
    try:
        subprocess.Popen(
            [chrome, f"--user-data-dir={profile_dir}", "--no-first-run", login_url],
            creationflags=CREATE_NO_WINDOW,
        )
        logger_func("[SUCCESS] Chrome sign-in page launched locally.")
    except Exception as e:
        logger_func(f"[ERROR] Chrome sign-in launch failed: {e}")
