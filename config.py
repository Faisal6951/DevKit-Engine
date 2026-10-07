# config.py

APP_NAME = "DevKit Engine"
APP_CODENAME = "Apex"
APP_VERSION = "2.0.0"
APP_ID = "Faisal6951.DevKitEngine.Apex.2"
ICON_NAME = "devkit-engine.ico"
REPO_URL = "https://github.com/Faisal6951/DevKit-Engine"
CF_UNICODETEXT = 13
CREATE_NO_WINDOW = 0x08000000
WINGET_INSTALL_TIMEOUT = 1800
WINGET_QUERY_TIMEOUT = 90

THEME = {
    "bg": "#070708",
    "surface": "#111214",
    "surface_alt": "#181A1D",
    "input": "#1C1E22",
    "border": "#2A2D33",
    "accent": "#E11D48",
    "accent_hover": "#BE123C",
    "accent_dim": "#3F0D1C",
    "text": "#F4F4F5",
    "muted": "#A1A1AA",
    "dim": "#71717A",
    "ok": "#34D399",
    "warn": "#FBBF24",
    "err": "#F87171",
    "white": "#FFFFFF",
    "black": "#000000",
}

DEFAULT_APPS = [
    {
        "key": "chrome",
        "display_name": "Google Chrome",
        "winget_id": "Google.Chrome",
        "category": "Browser",
        "purpose": "Primary web browser",
    },
    {
        "key": "firefox",
        "display_name": "Mozilla Firefox",
        "winget_id": "Mozilla.Firefox",
        "category": "Browser",
        "purpose": "Independent browser",
    },
    {
        "key": "brave",
        "display_name": "Brave",
        "winget_id": "Brave.Brave",
        "category": "Browser",
        "purpose": "Privacy-focused browser",
    },
    {
        "key": "git_bash",
        "display_name": "Git Bash",
        "winget_id": "Git.Git",
        "category": "Core",
        "purpose": "Version control",
    },
    {
        "key": "vscode",
        "display_name": "Visual Studio Code",
        "winget_id": "Microsoft.VisualStudioCode",
        "category": "Editor",
        "purpose": "Code editor",
    },
    {
        "key": "cursor",
        "display_name": "Cursor",
        "winget_id": "Anysphere.Cursor",
        "category": "Editor",
        "purpose": "AI-first IDE",
    },
    {
        "key": "docker",
        "display_name": "Docker Desktop",
        "winget_id": "Docker.DockerDesktop",
        "category": "Runtime",
        "purpose": "Containers",
    },
    {
        "key": "vlc",
        "display_name": "VLC Media Player",
        "winget_id": "VideoLAN.VLC",
        "category": "Media",
        "purpose": "Media player",
    },
]

STACK_PRESETS = {
    "recommended": ["chrome", "git_bash", "vscode", "cursor"],
    "full_stack": ["chrome", "git_bash", "vscode", "cursor", "docker", "firefox"],
    "browsers": ["chrome", "firefox", "brave"],
    "none": [],
}

DEFAULT_SELECTED = ["chrome", "git_bash", "vscode", "cursor"]
SECRET_CREDENTIAL_KEYS = ("github_token", "docker_password")
