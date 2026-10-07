# logic/deploy_engine.py
import os
import time
import threading
import subprocess

from config import DEFAULT_APPS, CREATE_NO_WINDOW, WINGET_INSTALL_TIMEOUT
from logic.system_tools import (
    is_internet_available,
    is_winget_available,
    generate_and_open_success_html,
    get_clipboard_text,
    build_install_index,
    find_chrome_path,
    format_duration,
    run_hidden,
)
from logic.auth_tools import authenticate_app


def install_package_id(package_id, logger_func):
    logger_func(f"[INSTALLER] Silent install: {package_id}")
    command = [
        "winget",
        "install",
        "--id",
        package_id,
        "--silent",
        "--disable-interactivity",
        "--accept-package-agreements",
        "--accept-source-agreements",
    ]
    try:
        process = run_hidden(command, timeout=WINGET_INSTALL_TIMEOUT)
        combined = f"{process.stdout or ''}\n{process.stderr or ''}".lower()
        if process.returncode == 0 or "already installed" in combined:
            logger_func(f"[SUCCESS] {package_id} is ready.")
            return True
        logger_func(f"[ERROR] WinGet failed for {package_id} (exit {process.returncode}).")
        return False
    except subprocess.TimeoutExpired:
        logger_func(f"[ERROR] WinGet timed out installing {package_id}.")
        return False
    except Exception as e:
        logger_func(f"[ERROR] Execution failed: {e}")
        return False


class DeploymentEngine:
    def __init__(self, ui_app):
        self.ui = ui_app
        self.clipboard_active = False
        self.cancel_event = threading.Event()
        self._clipboard_stop = threading.Event()

    def request_cancel(self):
        self.cancel_event.set()
        self._clipboard_stop.set()
        self.ui.log("[SYSTEM] Cancel requested — finishing the current package, then stopping.")

    def run_deployment(self):
        started = time.time()
        self.cancel_event.clear()
        self._clipboard_stop.clear()
        summary = {
            "installed": [],
            "skipped": [],
            "failed": [],
            "status": "success",
            "elapsed": "0s",
        }

        try:
            self.ui.log("─" * 46)
            self.ui.log("DEPLOYMENT SEQUENCE")
            self.ui.log("─" * 46)

            selected_list = self.ui.vault_data.get("selected_apps", [])
            custom_apps = self.ui.vault_data.get("custom_apps", [])
            if not selected_list and not custom_apps:
                self.ui.log("[WARN] Nothing is selected. Choose a stack or add a WinGet package.")
                self.ui.set_progress(0, "Standing by — nothing selected")
                return

            self.ui.log("[CHECK] Preflight: WinGet, network, package index...")
            if not is_winget_available():
                self.ui.log("[CRITICAL] WinGet is not available on this machine.")
                self.ui.log("[ERROR] Install App Installer from the Microsoft Store, then retry.")
                self.ui.set_progress(0, "Aborted — WinGet missing")
                summary["status"] = "failed"
                summary["failed"].append("WinGet unavailable")
                return

            if not is_internet_available():
                self.ui.log("[CRITICAL] No active internet connection detected.")
                self.ui.log("[ERROR] Operation safely aborted. Connect to a network.")
                self.ui.set_progress(0, "Aborted — no internet")
                summary["status"] = "failed"
                summary["failed"].append("No internet")
                return

            index = build_install_index()
            self.ui.after(0, lambda: self.ui.apply_install_index(index))

            jobs = []
            for app in DEFAULT_APPS:
                if app["key"] not in selected_list:
                    continue
                already = index.is_installed(app["display_name"], app["winget_id"])
                jobs.append({"kind": "builtin", "app": app, "already": already})
            for custom_id in custom_apps:
                already = index.is_installed(custom_id, custom_id)
                jobs.append({
                    "kind": "custom",
                    "app": {"key": custom_id, "display_name": custom_id, "winget_id": custom_id},
                    "already": already,
                })

            self.ui.log("")
            self.ui.log("[PLAN] Execution order")
            for job in jobs:
                mark = "skip" if job["already"] else "install"
                self.ui.log(f"  • {job['app']['display_name']}  [{mark}]")
            self.ui.log("")

            if not self.clipboard_active:
                self.start_clipboard_monitor()

            total = len(jobs)
            for step, job in enumerate(jobs, start=1):
                if self.cancel_event.is_set():
                    self.ui.log("[WARN] Remaining packages were skipped after cancel.")
                    summary["status"] = "cancelled"
                    break

                app = job["app"]
                name = app["display_name"]
                progress = (step - 1) / total
                self.ui.set_progress(progress, f"{step}/{total}  {name}")
                self.ui.log(f"[CHECK] {name}")

                installed_ok = True
                if job["already"]:
                    self.ui.log(f"[STATUS] {name} already present — skipped install.")
                    summary["skipped"].append(name)
                else:
                    self.ui.set_progress(progress + (0.45 / total), f"Installing {name}...")
                    installed_ok = install_package_id(app["winget_id"], self.ui.log)
                    if installed_ok:
                        summary["installed"].append(name)
                    else:
                        summary["failed"].append(name)

                if job["kind"] == "builtin" and installed_ok:
                    self.ui.set_progress(progress + (0.8 / total), f"Configuring {name}...")
                    authenticate_app(app["key"], self.ui.vault_data, self.ui.log, self.cancel_event)

                self.ui.set_run_stats(len(summary["installed"]), len(summary["skipped"]), len(summary["failed"]))
                self.ui.set_progress(step / total, f"Finished {name}")

            elapsed = format_duration(time.time() - started)
            summary["elapsed"] = elapsed
            if summary["status"] == "cancelled":
                headline = "DEPLOYMENT CANCELLED"
                status_text = f"Cancelled after {elapsed}"
            elif summary["failed"]:
                summary["status"] = "failed"
                headline = "DEPLOYMENT COMPLETED WITH ERRORS"
                status_text = f"Finished with issues · {elapsed}"
            else:
                headline = "DEPLOYMENT COMPLETED SUCCESSFULLY"
                status_text = f"Setup complete · {elapsed}"

            self.ui.log("")
            self.ui.log("─" * 46)
            self.ui.log(headline)
            self.ui.log(
                f"Installed {len(summary['installed'])} · "
                f"Skipped {len(summary['skipped'])} · "
                f"Failed {len(summary['failed'])} · {elapsed}"
            )
            self.ui.log("─" * 46)
            self.ui.set_progress(1.0 if summary["status"] != "cancelled" else 0.35, status_text)

            try:
                generate_and_open_success_html(self.ui.usb_dir, summary)
            except Exception as e:
                self.ui.log(f"[WARN] Could not launch success page: {e}")
        finally:
            self.stop_clipboard_monitor()
            self.ui.allow_sleep()
            self.ui.enable_deploy_btn()

    def start_clipboard_monitor(self):
        self.clipboard_active = True
        self._clipboard_stop.clear()
        threading.Thread(target=self.clipboard_monitor_loop, daemon=True).start()

    def stop_clipboard_monitor(self):
        self._clipboard_stop.set()
        self.clipboard_active = False

    def clipboard_monitor_loop(self):
        last_clip = ""
        profile_dir = os.path.join(self.ui.usb_dir, "DevKit", "profiles", "ChromeProfile")
        auth_keywords = [
            "cursor.com/cli-auth",
            "github.com/login",
            "spotify.com",
            "accounts.google.com",
            "login",
        ]

        while not self._clipboard_stop.is_set():
            clip_text = get_clipboard_text()
            if clip_text and clip_text != last_clip:
                last_clip = clip_text
                lowered = clip_text.lower()
                if any(kw in lowered for kw in auth_keywords) and clip_text.startswith("http"):
                    self.ui.log("[INTERCEPTED] Opening authentication URL in the DevKit Chrome profile...")
                    chrome_path = find_chrome_path() or r"C:\Program Files\Google\Chrome\Application\chrome.exe"
                    if os.path.exists(chrome_path):
                        os.makedirs(profile_dir, exist_ok=True)
                        subprocess.Popen(
                            [
                                chrome_path,
                                f"--user-data-dir={profile_dir}",
                                "--no-first-run",
                                clip_text,
                            ]
                        )
            self._clipboard_stop.wait(1.0)
