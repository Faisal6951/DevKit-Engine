# ui/launcher_ui.py
import os
import sys
import threading
import webbrowser
from datetime import datetime

import customtkinter as ctk
import tkinter as _tk

from config import (
    APP_NAME,
    APP_CODENAME,
    APP_VERSION,
    ICON_NAME,
    DEFAULT_APPS,
    STACK_PRESETS,
    THEME,
    REPO_URL,
)
from logic.system_tools import (
    get_usb_directory,
    load_vault,
    save_vault,
    prevent_sleep,
    allow_sleep,
    is_admin,
    is_winget_available,
    is_internet_available,
    build_install_index,
    resolve_winget_id,
)
from logic.deploy_engine import DeploymentEngine

T = THEME


class DevKitLauncher(ctk.CTk):
    def __init__(self):
        self._custom_icon = None
        super().__init__()

        ctk.set_appearance_mode("dark")
        self.configure(fg_color=T["bg"])

        self.usb_dir = get_usb_directory()
        self.vault_data = load_vault(self.usb_dir)
        self.engine = DeploymentEngine(self)
        self.install_index = None
        self.app_vars = {}
        self.app_badges = {}
        self.app_checks = {}
        self._lockable = []
        self._deploying = False
        self._secret_visible = {"git_token": False, "docker_pass": False}

        self.title(f"{APP_NAME} — {APP_CODENAME}")
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = min(1240, max(1080, int(screen_width * 0.72)))
        height = min(780, max(640, int(screen_height * 0.82)))
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(1040, 640)

        self.setup_ui_layout()
        self.load_settings_to_ui()
        self._lock_icon()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind("<Control-Return>", lambda e: self.start_deployment_thread())
        self.after(200, self.refresh_health)
        threading.Thread(target=self._bg_scan_installed, daemon=True).start()

    def _lock_icon(self):
        def resolve_icon():
            names = [ICON_NAME, "devkit-engine.ico", "apex.ico"]
            roots = []
            if hasattr(sys, "_MEIPASS"):
                roots.append(os.path.join(sys._MEIPASS, "assets"))
            roots.append(os.path.join(self.usb_dir, "assets"))
            for root in roots:
                for name in names:
                    path = os.path.join(root, name)
                    if os.path.exists(path):
                        return path
            return None

        icon = resolve_icon()
        if icon:
            self._custom_icon = icon
            try:
                _tk.Tk.wm_iconbitmap(self, bitmap=icon)
            except Exception:
                pass

    def iconbitmap(self, bitmap=None, **kwargs):
        if self._custom_icon and bitmap and bitmap != self._custom_icon:
            return
        super().iconbitmap(bitmap=bitmap, **kwargs)

    def _font(self, size=12, weight="normal"):
        return ctk.CTkFont(family="Segoe UI", size=size, weight=weight)

    def _mono(self, size=12):
        return ctk.CTkFont(family="Consolas", size=size)

    def setup_ui_layout(self):
        self._build_header()

        self.body = ctk.CTkFrame(self, fg_color=T["bg"], corner_radius=0)
        self.body.pack(fill="both", expand=True, padx=14, pady=(10, 8))
        self.body.grid_columnconfigure(0, weight=5, uniform="cols")
        self.body.grid_columnconfigure(1, weight=6, uniform="cols")
        self.body.grid_rowconfigure(0, weight=1)

        self.left_column = ctk.CTkScrollableFrame(
            self.body,
            fg_color=T["surface"],
            border_color=T["border"],
            border_width=1,
            corner_radius=12,
        )
        self.left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 7))

        self.right_column = ctk.CTkFrame(
            self.body,
            fg_color=T["surface"],
            border_color=T["border"],
            border_width=1,
            corner_radius=12,
        )
        self.right_column.grid(row=0, column=1, sticky="nsew", padx=(7, 0))

        self._build_stack_panel()
        self._build_custom_panel()
        self._build_creds_panel()
        self._build_ops_panel()
        self._build_footer()

    def _build_header(self):
        header = ctk.CTkFrame(self, height=64, corner_radius=0, fg_color="#050506")
        header.pack(side="top", fill="x")
        header.pack_propagate(False)

        brand = ctk.CTkFrame(header, fg_color="transparent")
        brand.pack(side="left", padx=18)
        ctk.CTkLabel(
            brand,
            text=APP_NAME.upper(),
            font=self._font(16, "bold"),
            text_color=T["text"],
        ).pack(side="left")
        ctk.CTkLabel(
            brand,
            text=f"  {APP_CODENAME}  ·  v{APP_VERSION}",
            font=self._font(12),
            text_color=T["dim"],
        ).pack(side="left", padx=(8, 0), pady=18)

        self.health = ctk.CTkFrame(header, fg_color="transparent")
        self.health.pack(side="left", padx=20)
        self.pill_admin = self._pill(self.health, "ADMIN")
        self.pill_winget = self._pill(self.health, "WINGET")
        self.pill_net = self._pill(self.health, "NETWORK")

        link = ctk.CTkLabel(
            header,
            text="GitHub ↗",
            font=self._font(12),
            text_color=T["muted"],
            cursor="hand2",
        )
        link.pack(side="right", padx=18)
        link.bind("<Button-1>", lambda e: webbrowser.open(REPO_URL))
        link.bind("<Enter>", lambda e: link.configure(text_color=T["accent"]))
        link.bind("<Leave>", lambda e: link.configure(text_color=T["muted"]))

    def _pill(self, parent, label):
        wrap = ctk.CTkFrame(parent, fg_color=T["surface_alt"], corner_radius=8, border_width=1, border_color=T["border"])
        wrap.pack(side="left", padx=4, pady=16)
        dot = ctk.CTkLabel(wrap, text="●", font=self._font(10), text_color=T["dim"], width=16)
        dot.pack(side="left", padx=(8, 0), pady=6)
        text = ctk.CTkLabel(wrap, text=label, font=self._font(10, "bold"), text_color=T["muted"])
        text.pack(side="left", padx=(2, 10))
        wrap.dot = dot
        wrap.text = text
        return wrap

    def _section_title(self, parent, title, subtitle=""):
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.pack(fill="x", padx=16, pady=(16, 6))
        ctk.CTkLabel(box, text=title, font=self._font(14, "bold"), text_color=T["text"]).pack(anchor="w")
        if subtitle:
            ctk.CTkLabel(box, text=subtitle, font=self._font(11), text_color=T["dim"]).pack(anchor="w")
        return box

    def _build_stack_panel(self):
        head = self._section_title(
            self.left_column,
            "1. Software stack",
            "Official WinGet packages only. Installed apps are skipped automatically.",
        )
        self.selection_label = ctk.CTkLabel(head, text="", font=self._font(11), text_color=T["accent"])
        self.selection_label.pack(anchor="w", pady=(4, 0))

        presets = ctk.CTkFrame(self.left_column, fg_color="transparent")
        presets.pack(fill="x", padx=16, pady=(0, 8))
        for key, label in (
            ("recommended", "Recommended"),
            ("full_stack", "Full stack"),
            ("browsers", "Browsers"),
            ("none", "Clear"),
        ):
            ctk.CTkButton(
                presets,
                text=label,
                width=96,
                height=28,
                fg_color=T["surface_alt"],
                hover_color=T["accent_dim"],
                text_color=T["text"],
                border_width=1,
                border_color=T["border"],
                font=self._font(11),
                command=lambda k=key: self.apply_preset(k),
            ).pack(side="left", padx=(0, 6))

        for app in DEFAULT_APPS:
            row = ctk.CTkFrame(
                self.left_column,
                fg_color=T["surface_alt"],
                corner_radius=10,
                border_width=1,
                border_color=T["border"],
            )
            row.pack(fill="x", padx=16, pady=3)
            var = ctk.StringVar(value="off")
            var.trace_add("write", lambda *_: self.update_selection_count())
            cb = ctk.CTkCheckBox(
                row,
                text=app["display_name"],
                variable=var,
                onvalue=app["key"],
                offvalue="off",
                text_color=T["text"],
                fg_color=T["accent"],
                hover_color=T["accent_hover"],
                border_width=1,
                border_color=T["border"],
                font=self._font(12),
            )
            cb.pack(side="left", padx=12, pady=10)
            ctk.CTkLabel(
                row,
                text=app["category"].upper(),
                font=self._font(10),
                text_color=T["dim"],
            ).pack(side="left", padx=(0, 8))
            badge = ctk.CTkLabel(row, text="SCANNING", font=self._font(10, "bold"), text_color=T["dim"])
            badge.pack(side="right", padx=12)
            self.app_vars[app["key"]] = var
            self.app_badges[app["key"]] = badge
            self.app_checks[app["key"]] = cb
            self._lockable.append(cb)

    def _build_custom_panel(self):
        self._section_title(
            self.left_column,
            "Custom WinGet package",
            "Paste a package ID or search by name. Press Enter to resolve.",
        )
        box = ctk.CTkFrame(self.left_column, fg_color="transparent")
        box.pack(fill="x", padx=16, pady=2)
        self.custom_app_entry = ctk.CTkEntry(
            box,
            placeholder_text="e.g. Spotify.Spotify  or  nodejs",
            fg_color=T["input"],
            border_color=T["border"],
            text_color=T["text"],
            font=self._font(12),
            height=36,
        )
        self.custom_app_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.custom_app_entry.bind("<Return>", lambda e: self.add_custom_app())
        self.custom_app_btn = ctk.CTkButton(
            box,
            text="Add",
            width=84,
            height=36,
            fg_color=T["white"],
            text_color=T["black"],
            hover_color="#D4D4D4",
            font=self._font(12, "bold"),
            command=self.add_custom_app,
        )
        self.custom_app_btn.pack(side="right")
        self._lockable.extend([self.custom_app_entry, self.custom_app_btn])
        self.custom_chips = ctk.CTkFrame(self.left_column, fg_color="transparent")
        self.custom_chips.pack(fill="x", padx=16, pady=(8, 4))

    def _build_creds_panel(self):
        self._section_title(
            self.left_column,
            "2. Sign-in automation (optional)",
            "Stored on this PC only. Secrets are protected with Windows DPAPI.",
        )
        self.g_email = self._labeled_entry(self.left_column, "Google account email", "example@gmail.com")
        self.git_user = self._labeled_entry(self.left_column, "GitHub username", "octocat")
        self.git_token, self.git_token_toggle = self._secret_entry(
            self.left_column, "GitHub token", "ghp_xxxxxxxxxxxx", "git_token"
        )
        self.docker_user = self._labeled_entry(self.left_column, "Docker Hub username", "docker-id")
        self.docker_pass, self.docker_pass_toggle = self._secret_entry(
            self.left_column, "Docker Hub password", "Password", "docker_pass"
        )
        self.btn_save_creds = ctk.CTkButton(
            self.left_column,
            text="Save vault locally",
            fg_color="transparent",
            text_color=T["text"],
            border_color=T["border"],
            border_width=1,
            hover_color=T["surface_alt"],
            height=36,
            font=self._font(12, "bold"),
            command=self.save_settings_from_ui,
        )
        self.btn_save_creds.pack(fill="x", padx=16, pady=(8, 18))
        self._lockable.extend([
            self.g_email, self.git_user, self.git_token, self.git_token_toggle,
            self.docker_user, self.docker_pass, self.docker_pass_toggle, self.btn_save_creds,
        ])

    def _labeled_entry(self, parent, label, placeholder, show=None):
        ctk.CTkLabel(parent, text=label, font=self._font(11), text_color=T["muted"]).pack(
            anchor="w", padx=16, pady=(8, 2)
        )
        entry = ctk.CTkEntry(
            parent,
            placeholder_text=placeholder,
            fg_color=T["input"],
            border_color=T["border"],
            text_color=T["text"],
            font=self._font(12),
            height=34,
            show=show if show else "",
        )
        entry.pack(fill="x", padx=16)
        return entry

    def _secret_entry(self, parent, label, placeholder, key):
        ctk.CTkLabel(parent, text=label, font=self._font(11), text_color=T["muted"]).pack(
            anchor="w", padx=16, pady=(8, 2)
        )
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=16)
        entry = ctk.CTkEntry(
            row,
            placeholder_text=placeholder,
            fg_color=T["input"],
            border_color=T["border"],
            text_color=T["text"],
            font=self._font(12),
            height=34,
            show="*",
        )
        entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        button = ctk.CTkButton(
            row,
            text="Show",
            width=70,
            height=34,
            fg_color=T["surface_alt"],
            hover_color=T["accent_dim"],
            text_color=T["muted"],
            border_width=1,
            border_color=T["border"],
            font=self._font(11),
            command=lambda: self.toggle_secret(key, entry, button),
        )
        button.pack(side="right")
        return entry, button

    def toggle_secret(self, key, entry, button):
        visible = not self._secret_visible.get(key, False)
        self._secret_visible[key] = visible
        entry.configure(show="" if visible else "*")
        button.configure(text="Hide" if visible else "Show")

    def _build_ops_panel(self):
        top = ctk.CTkFrame(self.right_column, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(top, text="Operations log", font=self._font(14, "bold"), text_color=T["text"]).pack(side="left")
        ctk.CTkButton(
            top,
            text="Copy",
            width=70,
            height=28,
            fg_color=T["surface_alt"],
            hover_color=T["accent_dim"],
            text_color=T["text"],
            border_width=1,
            border_color=T["border"],
            font=self._font(11),
            command=self.copy_log,
        ).pack(side="right")
        ctk.CTkButton(
            top,
            text="Clear",
            width=70,
            height=28,
            fg_color=T["surface_alt"],
            hover_color=T["accent_dim"],
            text_color=T["text"],
            border_width=1,
            border_color=T["border"],
            font=self._font(11),
            command=self.clear_log,
        ).pack(side="right", padx=(0, 6))

        self.console_out = ctk.CTkTextbox(
            self.right_column,
            fg_color="#0B0C0E",
            border_color=T["border"],
            border_width=1,
            text_color=T["muted"],
            font=self._mono(12),
            corner_radius=10,
        )
        self.console_out.pack(fill="both", expand=True, padx=16, pady=(0, 10))
        self.console_out.configure(state="disabled")
        tb = self.console_out._textbox
        tb.tag_config("ok", foreground=T["ok"])
        tb.tag_config("err", foreground=T["err"])
        tb.tag_config("warn", foreground=T["warn"])
        tb.tag_config("info", foreground="#7DD3FC")
        tb.tag_config("muted", foreground=T["dim"])

        stats = ctk.CTkFrame(self.right_column, fg_color="transparent")
        stats.pack(fill="x", padx=16, pady=(0, 8))
        self.stat_install = self._stat(stats, "INSTALL")
        self.stat_skip = self._stat(stats, "SKIP")
        self.stat_fail = self._stat(stats, "FAIL")

        self.progress_label = ctk.CTkLabel(
            self.right_column,
            text="Standing by",
            font=self._font(12, "bold"),
            text_color=T["text"],
        )
        self.progress_label.pack(anchor="w", padx=16, pady=(0, 6))
        self.progress_bar = ctk.CTkProgressBar(
            self.right_column,
            height=8,
            fg_color=T["surface_alt"],
            progress_color=T["accent"],
            corner_radius=8,
        )
        self.progress_bar.pack(fill="x", padx=16)
        self.progress_bar.set(0)

        deck = ctk.CTkFrame(self.right_column, fg_color="transparent")
        deck.pack(fill="x", padx=16, pady=14)
        self.btn_cancel = ctk.CTkButton(
            deck,
            text="Cancel",
            width=110,
            height=42,
            fg_color=T["surface_alt"],
            hover_color="#3F1D1D",
            text_color=T["text"],
            border_width=1,
            border_color=T["border"],
            font=self._font(13, "bold"),
            command=self.cancel_deployment,
            state="disabled",
        )
        self.btn_cancel.pack(side="left")
        self.btn_run = ctk.CTkButton(
            deck,
            text="Deploy environment",
            height=42,
            fg_color=T["accent"],
            hover_color=T["accent_hover"],
            font=self._font(14, "bold"),
            command=self.start_deployment_thread,
        )
        self.btn_run.pack(side="right", fill="x", expand=True, padx=(8, 0))

    def _stat(self, parent, label):
        card = ctk.CTkFrame(parent, fg_color=T["surface_alt"], corner_radius=8, border_width=1, border_color=T["border"])
        card.pack(side="left", expand=True, fill="x", padx=(0, 8))
        ctk.CTkLabel(card, text=label, font=self._font(10, "bold"), text_color=T["dim"]).pack(anchor="w", padx=10, pady=(8, 0))
        value = ctk.CTkLabel(card, text="0", font=self._font(18, "bold"), text_color=T["text"])
        value.pack(anchor="w", padx=10, pady=(0, 8))
        return value

    def _build_footer(self):
        foot = ctk.CTkFrame(self, height=32, fg_color="#050506", corner_radius=0)
        foot.pack(side="bottom", fill="x")
        ctk.CTkLabel(
            foot,
            text="Developed by Faisal Adnan & Team  ·  Ctrl+Enter to deploy  ·  Credentials never leave this machine",
            font=self._font(11),
            text_color=T["dim"],
        ).pack(side="left", padx=16, pady=6)

    def set_health_pill(self, pill, ok):
        color = T["ok"] if ok else T["err"]
        pill.dot.configure(text_color=color)

    def refresh_health(self):
        self.set_health_pill(self.pill_admin, is_admin())
        self.set_health_pill(self.pill_winget, is_winget_available())
        self.set_health_pill(self.pill_net, is_internet_available())

    def _bg_scan_installed(self):
        try:
            index = build_install_index()
            self.after(0, lambda: self.apply_install_index(index))
            self.after(0, lambda: self.log("[INIT] Package index ready — already-installed apps are marked."))
        except Exception as e:
            self.after(0, lambda: self.log(f"[WARN] Could not scan installed apps: {e}"))

    def apply_install_index(self, index):
        self.install_index = index
        if index is None:
            return
        for app in DEFAULT_APPS:
            badge = self.app_badges.get(app["key"])
            if not badge:
                continue
            if index.is_installed(app["display_name"], app["winget_id"]):
                badge.configure(text="INSTALLED", text_color=T["ok"])
            else:
                badge.configure(text="READY", text_color=T["dim"])

    def apply_preset(self, key):
        wanted = set(STACK_PRESETS.get(key, []))
        for app_key, var in self.app_vars.items():
            var.set(app_key if app_key in wanted else "off")
        self.log(f"[INFO] Preset applied: {key.replace('_', ' ')}")

    def update_selection_count(self):
        selected = self.selected_app_keys()
        custom = len(self.vault_data.get("custom_apps", []))
        total = len(selected) + custom
        if getattr(self, "selection_label", None):
            self.selection_label.configure(text=f"{len(selected)} bundled  ·  {custom} custom  ·  {total} queued")
        if getattr(self, "btn_run", None) and not self._deploying:
            label = "Deploy environment" if total == 0 else f"Deploy {total} package{'s' if total != 1 else ''}"
            self.btn_run.configure(text=label)

    def selected_app_keys(self):
        return [key for key, var in self.app_vars.items() if var.get() != "off"]

    def prevent_sleep(self):
        prevent_sleep()
        self.log("[SYSTEM] Power policy engaged: preventing sleep.")

    def allow_sleep(self):
        allow_sleep()
        self.log("[SYSTEM] Power policy restored.")

    def set_progress(self, percentage, status_text):
        def update():
            self.progress_bar.configure(mode="determinate")
            self.progress_bar.stop()
            self.progress_bar.set(max(0.0, min(1.0, float(percentage))))
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

    def _log_tag(self, message):
        upper = message.upper()
        if "[SUCCESS]" in upper or "COMPLETED SUCCESSFULLY" in upper:
            return "ok"
        if "[ERROR]" in upper or "[CRITICAL]" in upper or "WITH ERRORS" in upper:
            return "err"
        if "[WARN]" in upper or "CANCELLED" in upper:
            return "warn"
        if "[CHECK]" in upper or "[PLAN]" in upper or "[INFO]" in upper or "[INIT]" in upper:
            return "info"
        return "muted"

    def log(self, message):
        stamp = datetime.now().strftime("%H:%M:%S")
        line = f"{stamp}  {message}\n"
        tag = self._log_tag(message)

        def update():
            self.console_out.configure(state="normal")
            try:
                self.console_out._textbox.insert("end", line, tag)
            except Exception:
                self.console_out.insert("end", line)
            self.console_out.see("end")
            self.console_out.configure(state="disabled")
        self.after(0, update)

    def set_run_stats(self, installed, skipped, failed):
        def update():
            self.stat_install.configure(text=str(installed))
            self.stat_skip.configure(text=str(skipped))
            self.stat_fail.configure(text=str(failed))
        self.after(0, update)

    def reset_stats(self):
        self.set_run_stats(0, 0, 0)

    def clear_log(self):
        self.console_out.configure(state="normal")
        self.console_out.delete("1.0", "end")
        self.console_out.configure(state="disabled")

    def copy_log(self):
        text = self.console_out.get("1.0", "end").strip()
        self.clipboard_clear()
        self.clipboard_append(text)
        self.log("[INFO] Log copied to clipboard.")

    def enable_deploy_btn(self):
        def restore():
            self._deploying = False
            self.btn_run.configure(state="normal")
            self.btn_cancel.configure(state="disabled")
            self._set_inputs_enabled(True)
            self.update_selection_count()
        self.after(0, restore)

    def _set_inputs_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        for widget in self._lockable:
            try:
                widget.configure(state=state)
            except Exception:
                continue

    def load_settings_to_ui(self):
        selected = set(self.vault_data.get("selected_apps", []))
        for key, var in self.app_vars.items():
            var.set(key if key in selected else "off")
        self.refresh_custom_apps_display()

        creds = self.vault_data.get("credentials", {})
        fields = (
            (self.g_email, creds.get("google_email", "")),
            (self.git_user, creds.get("git_username", "")),
            (self.git_token, creds.get("github_token", "")),
            (self.docker_user, creds.get("docker_username", "")),
            (self.docker_pass, creds.get("docker_password", "")),
        )
        for entry, value in fields:
            entry.delete(0, "end")
            if value:
                entry.insert(0, value)

        self.update_selection_count()
        self.log(f"[INIT] {APP_NAME} {APP_CODENAME} v{APP_VERSION} ready.")

    def save_settings_from_ui(self, quiet=False):
        self.vault_data["selected_apps"] = self.selected_app_keys()
        self.vault_data["credentials"] = {
            "google_email": self.g_email.get().strip(),
            "git_username": self.git_user.get().strip(),
            "github_token": self.git_token.get().strip(),
            "docker_username": self.docker_user.get().strip(),
            "docker_password": self.docker_pass.get().strip(),
        }
        ok = save_vault(self.usb_dir, self.vault_data)
        if not quiet:
            if ok:
                self.log("[VAULT] Credentials saved locally. Secrets sealed with Windows DPAPI.")
            else:
                self.log("[ERROR] Could not write the local vault file.")
        return ok

    def add_custom_app(self):
        raw_query = self.custom_app_entry.get().strip()
        if not raw_query:
            return
        self.custom_app_btn.configure(state="disabled")
        self.set_indeterminate_pulse(f"Resolving {raw_query}...")
        threading.Thread(target=self.bg_resolve_custom_app, args=(raw_query,), daemon=True).start()

    def bg_resolve_custom_app(self, raw_query):
        try:
            resolved_id = resolve_winget_id(raw_query)
            if resolved_id:
                if "custom_apps" not in self.vault_data:
                    self.vault_data["custom_apps"] = []
                if resolved_id not in self.vault_data["custom_apps"]:
                    self.vault_data["custom_apps"].append(resolved_id)
                    save_vault(self.usb_dir, self.vault_data)
                    self.after(0, self.refresh_custom_apps_display)
                    self.after(0, lambda: self.custom_app_entry.delete(0, "end"))
                    self.log(f"[SUCCESS] Mapped custom package: {resolved_id}")
                else:
                    self.log(f"[INFO] '{resolved_id}' is already in the queue.")
            else:
                self.log(f"[WARN] No WinGet match for '{raw_query}'. Try the exact package ID.")
        except Exception as e:
            self.log(f"[ERROR] Query failed: {e}")
        finally:
            self.stop_progress_pulse()
            self.set_progress(0, "Standing by")
            self.after(0, lambda: self.custom_app_btn.configure(state="disabled" if self._deploying else "normal"))
            self.after(0, self.update_selection_count)

    def refresh_custom_apps_display(self):
        for child in self.custom_chips.winfo_children():
            child.destroy()
        custom_apps = self.vault_data.get("custom_apps", [])
        if not custom_apps:
            ctk.CTkLabel(
                self.custom_chips,
                text="No custom packages yet.",
                font=self._font(11),
                text_color=T["dim"],
            ).pack(anchor="w")
            self.update_selection_count()
            return
        for package_id in custom_apps:
            chip = ctk.CTkFrame(
                self.custom_chips,
                fg_color=T["surface_alt"],
                corner_radius=8,
                border_width=1,
                border_color=T["border"],
            )
            chip.pack(fill="x", pady=3)
            ctk.CTkLabel(chip, text=package_id, font=self._mono(12), text_color=T["text"]).pack(
                side="left", padx=10, pady=6
            )
            ctk.CTkButton(
                chip,
                text="Remove",
                width=72,
                height=26,
                fg_color="transparent",
                hover_color="#3F1D1D",
                text_color=T["muted"],
                font=self._font(11),
                command=lambda pid=package_id: self.remove_custom_app(pid),
            ).pack(side="right", padx=6)
        self.update_selection_count()

    def remove_custom_app(self, package_id):
        apps = self.vault_data.get("custom_apps", [])
        self.vault_data["custom_apps"] = [item for item in apps if item != package_id]
        save_vault(self.usb_dir, self.vault_data)
        self.refresh_custom_apps_display()
        self.log(f"[INFO] Removed {package_id} from the queue.")

    def start_deployment_thread(self):
        if self._deploying:
            return
        self.save_settings_from_ui(quiet=True)
        if not self.selected_app_keys() and not self.vault_data.get("custom_apps"):
            self.log("[WARN] Select at least one package before deploying.")
            return
        self._deploying = True
        self.reset_stats()
        self.btn_run.configure(state="disabled", text="Deploying...")
        self.btn_cancel.configure(state="normal")
        self._set_inputs_enabled(False)
        self.prevent_sleep()
        self.refresh_health()
        threading.Thread(target=self.engine.run_deployment, daemon=True).start()

    def cancel_deployment(self):
        if self._deploying:
            self.engine.request_cancel()
            self.btn_cancel.configure(state="disabled")

    def on_close(self):
        try:
            self.engine.cancel_event.set()
            self.engine.stop_clipboard_monitor()
            allow_sleep()
        except Exception:
            pass
        self.destroy()
