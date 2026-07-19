# ui/launcher_ui.py
import threading
import os
import re
import webbrowser
import subprocess
import customtkinter as ctk

from config import DEFAULT_APPS, APP_NAME , ICON_NAME
from logic.system_tools import (
    get_usb_directory, load_vault, save_vault,
    prevent_sleep, allow_sleep
)
from logic.deploy_engine import DeploymentEngine

class DevKitLauncher(ctk.CTk):
    def __init__(self):
        self._custom_icon = None
        super().__init__()

        self.usb_dir = get_usb_directory()
        self.vault_data = load_vault(self.usb_dir)

        self.title("Dev-Kit Setup Engine")

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        width = 1024
        height = min(540, int(screen_height * 0.75))
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        self.geometry(f"{width}x{height}+{x}+{y}")
        self.resizable(False, False)

        self.clipboard_active = False
        self.app_checkboxes = {}
        self.setup_ui_layout()
        self.load_settings_to_ui()

        # ── Icon: sharp on all DPI scales ───────────────────────────────────
        _ico = os.path.join(self.usb_dir, "assets", "devkit-engine.ico")
        if os.path.exists(_ico):
            self._custom_icon = _ico
            import tkinter as _tk

            try:
                _tk.Tk.wm_iconbitmap(self, bitmap=_ico)
            except Exception:
                pass

    def iconbitmap(self, bitmap=None, **kwargs):
        """
        CustomTkinter calls self.iconbitmap(CTK_ICON) internally via after(200).
        This intercepts that call and blocks it so our icon stays locked.
        """
        if self._custom_icon and bitmap and bitmap != self._custom_icon:
            return  # CTK is trying to reset to its own icon — block it
        super().iconbitmap(bitmap=bitmap, **kwargs)

    def setup_ui_layout(self):
        # TOP BAR
        self.top_bar = ctk.CTkFrame(self, height=45, corner_radius=0, fg_color="#050505")
        self.top_bar.pack(side="top", fill="x")
        
        self.sec_badge = ctk.CTkLabel(self.top_bar, text="SYSTEM CONFIGURATION", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#FFFFFF")
        self.sec_badge.pack(side="left", padx=15)
        
        self.creator_link = ctk.CTkLabel(self.top_bar, text="⚡ Developed by Faisal Adnan & Team", font=ctk.CTkFont(family="Segoe UI", size=10, underline=True), text_color="#737373", cursor="hand2")
        self.creator_link.pack(side="right", padx=15)
        self.creator_link.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/Faisal6951/DevKit-Engine"))
        
        self.body = ctk.CTkFrame(self, corner_radius=0, fg_color="#0A0A0A")
        self.body.pack(fill="both", expand=True, padx=12, pady=12)
        
        self.left_column = ctk.CTkScrollableFrame(self.body, width=420, fg_color="#121212", border_color="#262626", border_width=1, corner_radius=2)
        self.left_column.pack(side="left", fill="both", expand=True, padx=(0, 6))
        
        self.right_column = ctk.CTkFrame(self.body, fg_color="#121212", border_color="#262626", border_width=1, corner_radius=2)
        self.right_column.pack(side="right", fill="both", expand=True, padx=(6, 0))
        
        # LEFT PANEL: SELECTIONS
        self.lbl_step1 = ctk.CTkLabel(self.left_column, text="1. Select Software Stack", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color="#FFFFFF")
        self.lbl_step1.pack(anchor="w", padx=12, pady=(12, 6))
        
        for app in DEFAULT_APPS:
            var = ctk.StringVar(value="off")
            cb = ctk.CTkCheckBox(self.left_column, text=app["display_name"], variable=var, onvalue=app["key"], offvalue="off", text_color="#A3A3A3", border_width=1, font=ctk.CTkFont(family="Segoe UI", size=11))
            cb.pack(anchor="w", padx=20, pady=4)
            self.app_checkboxes[app["key"]] = var
            
        self.lbl_custom = ctk.CTkLabel(self.left_column, text="Add Custom WinGet Application:", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#A3A3A3")
        self.lbl_custom.pack(anchor="w", padx=12, pady=(15, 4))
        
        self.custom_box_frame = ctk.CTkFrame(self.left_column, fg_color="transparent")
        self.custom_box_frame.pack(fill="x", padx=12, pady=2)
        
        self.custom_app_entry = ctk.CTkEntry(self.custom_box_frame, placeholder_text="e.g. spotify, yt-dlp", fg_color="#1A1A1A", border_color="#404040", text_color="#FFFFFF", font=ctk.CTkFont(family="Segoe UI", size=11))
        self.custom_app_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        
        self.custom_app_btn = ctk.CTkButton(self.custom_box_frame, text="+ Add", width=70, fg_color="#FFFFFF", text_color="#000000", hover_color="#D4D4D4", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), command=self.add_custom_app)
        self.custom_app_btn.pack(side="right")
        
        self.custom_list_box = ctk.CTkTextbox(self.left_column, height=80, fg_color="#1A1A1A", border_color="#404040", border_width=1, text_color="#A3A3A3", font=ctk.CTkFont(family="Consolas", size=11))
        self.custom_list_box.pack(fill="x", padx=12, pady=(6, 10))
        
        # LEFT PANEL: CREDENTIALS
        self.lbl_step2 = ctk.CTkLabel(self.left_column, text="2. Setup Sign-In Automation (Optional)", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color="#FFFFFF")
        self.lbl_step2.pack(anchor="w", padx=12, pady=(15, 6))

        self.lbl_google = ctk.CTkLabel(self.left_column, text="Google Account Email:", font=ctk.CTkFont(family="Segoe UI", size=11), text_color="#A3A3A3")
        self.lbl_google.pack(anchor="w", padx=12, pady=(4, 2))
        self.g_email = ctk.CTkEntry(self.left_column, placeholder_text="example@gmail.com", fg_color="#1A1A1A", border_color="#404040", text_color="#FFFFFF", font=ctk.CTkFont(family="Segoe UI", size=11))
        self.g_email.pack(fill="x", padx=12, pady=(0, 10))

        self.lbl_github_user = ctk.CTkLabel(self.left_column, text="GitHub Username:", font=ctk.CTkFont(family="Segoe UI", size=11), text_color="#A3A3A3")
        self.lbl_github_user.pack(anchor="w", padx=12, pady=(4, 2))
        self.git_user = ctk.CTkEntry(self.left_column, placeholder_text="GitHub Username", fg_color="#1A1A1A", border_color="#404040", text_color="#FFFFFF", font=ctk.CTkFont(family="Segoe UI", size=11))
        self.git_user.pack(fill="x", padx=12, pady=(0, 10))

        self.lbl_github_token = ctk.CTkLabel(self.left_column, text="GitHub Token (ghp_...):", font=ctk.CTkFont(family="Segoe UI", size=11), text_color="#A3A3A3")
        self.lbl_github_token.pack(anchor="w", padx=12, pady=(4, 2))
        self.git_token = ctk.CTkEntry(self.left_column, placeholder_text="ghp_xxxxxxxxxxxx", show="*", fg_color="#1A1A1A", border_color="#404040", text_color="#FFFFFF", font=ctk.CTkFont(family="Segoe UI", size=11))
        self.git_token.pack(fill="x", padx=12, pady=(0, 10))

        self.lbl_docker_user = ctk.CTkLabel(self.left_column, text="Docker Hub Username:", font=ctk.CTkFont(family="Segoe UI", size=11), text_color="#A3A3A3")
        self.lbl_docker_user.pack(anchor="w", padx=12, pady=(4, 2))
        self.docker_user = ctk.CTkEntry(self.left_column, placeholder_text="Docker Hub Username", fg_color="#1A1A1A", border_color="#404040", text_color="#FFFFFF", font=ctk.CTkFont(family="Segoe UI", size=11))
        self.docker_user.pack(fill="x", padx=12, pady=(0, 10))

        self.lbl_docker_pass = ctk.CTkLabel(self.left_column, text="Docker Hub Password:", font=ctk.CTkFont(family="Segoe UI", size=11), text_color="#A3A3A3")
        self.lbl_docker_pass.pack(anchor="w", padx=12, pady=(4, 2))
        self.docker_pass = ctk.CTkEntry(self.left_column, placeholder_text="Password", show="*", fg_color="#1A1A1A", border_color="#404040", text_color="#FFFFFF", font=ctk.CTkFont(family="Segoe UI", size=11))
        self.docker_pass.pack(fill="x", padx=12, pady=(0, 15))

        self.btn_save_creds = ctk.CTkButton(self.left_column, text="Save Vault Credentials", fg_color="transparent", text_color="#FFFFFF", border_color="#404040", border_width=1, hover_color="#1A1A1A", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), command=self.save_settings_from_ui)
        self.btn_save_creds.pack(fill="x", padx=12, pady=(0, 15))

        # RIGHT PANEL: LOGS
        self.lbl_out = ctk.CTkLabel(self.right_column, text="System Log", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#FFFFFF")
        self.lbl_out.pack(anchor="w", padx=12, pady=(12, 4))
        
        self.console_out = ctk.CTkTextbox(self.right_column, fg_color="#0A0A0A", border_color="#262626", border_width=1, text_color="#A3A3A3", font=ctk.CTkFont(family="Consolas", size=11))
        self.console_out.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self.console_out.configure(state="disabled")
        
        self.progress_frame = ctk.CTkFrame(self.right_column, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=12, pady=(0, 10))
        
        self.progress_label = ctk.CTkLabel(self.progress_frame, text="Current State: Standing By...", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#FFFFFF")
        self.progress_label.pack(anchor="w", pady=(0, 4))
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, height=6, fg_color="#262626", progress_color="#E11D48")
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0)

        self.deck = ctk.CTkFrame(self.right_column, fg_color="transparent")
        self.deck.pack(fill="x", padx=12, pady=(0, 12))
        
        self.btn_run = ctk.CTkButton(self.deck, text="Deploy Environment", fg_color="#E11D48", hover_color="#BE123C", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), command=self.start_deployment_thread)
        self.btn_run.pack(side="right", fill="x", expand=True, padx=(3, 0))

    def prevent_sleep(self):
        prevent_sleep()
        self.log("[SYSTEM] Power policy engaged: Preventing system sleep.")

    def allow_sleep(self):
        allow_sleep()
        self.log("[SYSTEM] Power policy restored: Normal sleep allowed.")

    def set_progress(self, percentage, status_text):
        def update():
            self.progress_bar.configure(mode="determinate")
            self.progress_bar.set(percentage)
            self.progress_label.configure(text=status_text)
        self.after(0, update)

    def set_indeterminate_pulse(self, status_text):
        def update():
            self.progress_label.configure(text=status_text)
            self.progress_bar.configure(mode="indeterminate")
            self.progress_bar.start()
        self.after(0, update)

    def stop_progress_pulse(self):
        def update():
            self.progress_bar.stop()
            self.progress_bar.configure(mode="determinate")
        self.after(0, update)

    def log(self, message):
        def update():
            self.console_out.configure(state="normal")
            self.console_out.insert("end", f"{message}\n")
            self.console_out.see("end")
            self.console_out.configure(state="disabled")
        self.after(0, update)

    def enable_deploy_btn(self):
        self.after(0, lambda: self.btn_run.configure(state="normal"))

    def load_settings_to_ui(self):
        for key, var in self.app_checkboxes.items():
            if key in self.vault_data.get("selected_apps", []):
                var.set(key)
            else:
                var.set("off")
        self.refresh_custom_apps_display()
        
        creds = self.vault_data.get("credentials", {})
        self.g_email.insert(0, creds.get("google_email", ""))
        self.git_user.insert(0, creds.get("git_username", ""))
        self.git_token.insert(0, creds.get("github_token", ""))
        self.docker_user.insert(0, creds.get("docker_username", ""))
        self.docker_pass.insert(0, creds.get("docker_password", ""))
        
        self.log(f"[INIT] Interface built successfully.")

    def save_settings_from_ui(self):
        selected = [key for key, var in self.app_checkboxes.items() if var.get() != "off"]
        self.vault_data["selected_apps"] = selected
        
        self.vault_data["credentials"] = {
            "google_email": self.g_email.get().strip(),
            "git_username": self.git_user.get().strip(),
            "github_token": self.git_token.get().strip(),
            "docker_username": self.docker_user.get().strip(),
            "docker_password": self.docker_pass.get().strip()
        }
        save_vault(self.usb_dir, self.vault_data)

    def add_custom_app(self):
        raw_query = self.custom_app_entry.get().strip()
        if not raw_query: return
        self.custom_app_btn.configure(state="disabled")
        self.set_indeterminate_pulse(f"Querying sources for: {raw_query}")
        threading.Thread(target=self.bg_resolve_custom_app, args=(raw_query,), daemon=True).start()

    def bg_resolve_custom_app(self, raw_query):
        try:
            result = subprocess.run(["winget", "search", raw_query, "--accept-source-agreements"], stdout=subprocess.PIPE, text=True, shell=True, creationflags=0x08000000)
            lines = result.stdout.splitlines()
            resolved_id = None
            for line in lines:
                if "---" in line or "Name" in line or not line.strip(): continue
                match = re.search(r'\b([A-Za-z0-9-]+\.[A-Za-z0-9-]+)\b', line)
                if match:
                    resolved_id = match.group(1)
                    break
            if resolved_id:
                if "custom_apps" not in self.vault_data: self.vault_data["custom_apps"] = []
                if resolved_id not in self.vault_data["custom_apps"]:
                    self.vault_data["custom_apps"].append(resolved_id)
                    save_vault(self.usb_dir, self.vault_data)
                    self.after(0, self.refresh_custom_apps_display)
                    self.after(0, lambda: self.custom_app_entry.delete(0, "end"))
                    self.log(f"[SUCCESS] Mapped: {resolved_id}")
                else: self.log(f"[INFO] '{resolved_id}' is already registered.")
            else: self.log(f"[WARN] No match found for: '{raw_query}'")
        except Exception as e: self.log(f"[ERROR] Query failed: {e}")
        finally:
            self.stop_progress_pulse()
            self.set_progress(0, "Standing By...")
            self.after(0, lambda: self.custom_app_btn.configure(state="normal"))

    def refresh_custom_apps_display(self):
        self.custom_list_box.configure(state="normal")
        self.custom_list_box.delete("1.0", "end")
        custom_apps = self.vault_data.get("custom_apps", [])
        if not custom_apps:
            self.custom_list_box.insert("1.0", "No custom packages configured.")
        else:
            self.custom_list_box.insert("1.0", "\n".join(custom_apps))
        self.custom_list_box.configure(state="disabled")

    def start_deployment_thread(self):
        self.save_settings_from_ui()
        self.after(0, lambda: self.btn_run.configure(state="disabled"))
        self.prevent_sleep()
        threading.Thread(target=self.engine.run_deployment, daemon=True).start()