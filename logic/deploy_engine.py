# logic/deploy_engine.py
import os
import time
import subprocess
import threading
from config import DEFAULT_APPS
from logic.system_tools import (
    is_internet_available, generate_and_open_success_html, 
    get_clipboard_text, is_app_installed
)
from logic.auth_tools import authenticate_app

def install_package_id(package_id, logger_func):
    logger_func(f"[INSTALLER] Running silent installation: {package_id}...")
    command = [
        "winget", "install",
        "--id", package_id,
        "--silent",
        "--force",
        "--disable-interactivity",
        "--accept-package-agreements",
        "--accept-source-agreements"
    ]
    try:
        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True, creationflags=0x08000000)
        if process.returncode == 0:
            logger_func(f"[SUCCESS] {package_id} successfully installed.")
            return True
        else:
            logger_func(f"[ERROR] WinGet failed (Exit code: {process.returncode}).")
            return False
    except Exception as e:
        logger_func(f"[ERROR] Execution failed: {e}")
        return False


class DeploymentEngine:
    def __init__(self, ui_app):
        self.ui = ui_app
        self.clipboard_active = False

    def run_deployment(self):
        self.ui.log("\n" + "="*50)
        self.ui.log("      INITIALIZING DEPLOYMENT SEQUENCE     ")
        self.ui.log("="*50)
        
        self.ui.log("[CHECK] Verifying internet connectivity...")
        if not is_internet_available():
            self.ui.log("\n[CRITICAL] No active internet connection detected!")
            self.ui.log("[ERROR] Operation safely aborted. Connect to a network.")
            self.ui.log("\n" + "="*50)
            self.ui.set_progress(0, "Deploy Aborted - No Internet")
            self.ui.allow_sleep()
            self.ui.enable_deploy_btn()
            return
        
        if not self.clipboard_active:
            self.start_clipboard_monitor()

        self.sync_app_stack()

        self.ui.log("\n" + "="*50)
        self.ui.log("       DEPLOYMENT COMPLETED SUCCESSFULLY         ")
        self.ui.log("="*50 + "\n")
        
        self.ui.allow_sleep()
        self.ui.set_progress(1.0, "Deploy Finished - Setup Complete!")
        
        try:
            generate_and_open_success_html(self.ui.usb_dir)
        except Exception as e:
            self.ui.log(f"[WARN] Could not launch success page: {e}")

        self.ui.enable_deploy_btn()

    def start_clipboard_monitor(self):
        self.clipboard_active = True
        threading.Thread(target=self.clipboard_monitor_loop, daemon=True).start()

    def clipboard_monitor_loop(self):
        last_clip = ""
        profile_dir = os.path.join(self.ui.usb_dir, "DevKit", "profiles", "ChromeProfile")
        auth_keywords = ["cursor.com/cli-auth", "github.com/login", "spotify.com", "accounts.google.com", "login"]

        while True:
            clip_text = get_clipboard_text()
            if clip_text and clip_text != last_clip:
                last_clip = clip_text
                if any(kw in clip_text.lower() for kw in auth_keywords) and clip_text.startswith("http"):
                    self.ui.log(f"\n[INTERCEPTED] Redirecting authentication payload...")
                    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
                    if os.path.exists(chrome_path):
                        subprocess.Popen([
                            chrome_path,
                            f"--user-data-dir={profile_dir}",
                            "--no-first-run",
                            clip_text
                        ])
            time.sleep(1)

    def sync_app_stack(self):
        selected_list = self.ui.vault_data.get("selected_apps", [])
        custom_apps = self.ui.vault_data.get("custom_apps", [])
        
        total_tasks = len(selected_list) + len(custom_apps)
        if total_tasks == 0: return
            
        task_weight = 1.0 / total_tasks
        current_step = 0

        for app in DEFAULT_APPS:
            if app["key"] not in selected_list: continue
            current_step += 1
            
            self.ui.log(f"\n[CHECK] Searching system for: {app['display_name']}...")
            
            if is_app_installed(app["display_name"], app["winget_id"]):
                self.ui.log(f"[STATUS] {app['display_name']} already exists. Skipping install.")
            else:
                self.ui.log(f"[INSTALLER] {app['display_name']} not found. Installing...")
                install_progress = (current_step - 1) * task_weight + (task_weight * 0.4)
                self.ui.set_progress(install_progress, f"Installing {app['display_name']}...")
                install_package_id(app["winget_id"], self.ui.log)
            
            auth_progress = (current_step - 1) * task_weight + (task_weight * 0.8)
            self.ui.set_progress(auth_progress, f"Configuring {app['display_name']} Auth...")
            authenticate_app(app["key"], self.ui.vault_data, self.ui.log)
            
            self.ui.set_progress(current_step * task_weight, f"Finished {app['display_name']}")

        if custom_apps:
            for custom_id in custom_apps:
                current_step += 1
                if is_app_installed(custom_id, custom_id): 
                    self.ui.log(f"[STATUS] {custom_id} already exists. Skipping.")
                else:
                    self.ui.log(f"[INSTALLER] {custom_id} not found. Installing...")
                    install_package_id(custom_id, self.ui.log)
                self.ui.set_progress(current_step * task_weight, f"Finished: {custom_id}")