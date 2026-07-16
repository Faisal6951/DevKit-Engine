# logic/auth_tools.py
import os
import subprocess
import time

def authenticate_app(app_key, vault_data, logger_func):
    creds = vault_data.get("credentials", {})
    if app_key == "git_bash":
        user, token = creds.get("git_username", ""), creds.get("github_token", "")
        if not user or not token: return
        
        logger_func("[AUTOMATION] Writing global Git settings...")
        try:
            subprocess.run(["git", "config", "--global", "user.name", user], check=True, shell=True, creationflags=0x08000000)
            subprocess.run(["git", "config", "--global", "credential.helper", "store"], check=True, shell=True, creationflags=0x08000000)
            user_profile = os.environ.get("USERPROFILE", "C:\\Users\\Default")
            with open(os.path.join(user_profile, ".git-credentials"), "w") as f:
                f.write(f"https://{user}:{token}@github.com\n")
            logger_func("[SUCCESS] Git credentials mapped.")
        except Exception as e: 
            logger_func(f"[ERROR] Git setup failed: {e}")
            
    elif app_key == "docker":
        user, password = creds.get("docker_username", ""), creds.get("docker_password", "")
        if not user or not password: return
        logger_func("[AUTOMATION] Launching Docker Daemon session...")
        try:
            subprocess.Popen("start docker-desktop://", shell=True)
            time.sleep(3)
            process = subprocess.Popen(["docker", "login", "-u", user, "--password-stdin"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True, creationflags=0x08000000)
            stdout, stderr = process.communicate(input=password)
            if process.returncode == 0: 
                logger_func("[SUCCESS] Docker automation completed.")
            else: 
                logger_func(f"[ERROR] Docker returned exit code: {stderr.strip() or stdout.strip()}")
        except Exception as e: 
            logger_func(f"[ERROR] Docker login failed: {e}")