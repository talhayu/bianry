import platform
import os
import subprocess
import requests
import time
from pyngrok import ngrok,conf

conf.get_default().auth_token = '2jdJDapQWBBC4C5KT9xG6HIoVKg_NCCB2jh49izGVFnteLTG'

# ──────────────────────────────────────────────
# Config — change SERVER_URL when deploying
# ──────────────────────────────────────────────
SERVER_URL = "https://5ade-103-117-160-9.ngrok-free.app"
USER_ID = "test-user-123"  # hardcoded for testing


# ──────────────────────────────────────────────
# OS Detection
# ──────────────────────────────────────────────
def get_os():
    SYSTEM_MAP = {
        "Darwin": "mac",
        "Linux": "linux",
        "Windows": "windows",
    }
    return SYSTEM_MAP.get(platform.system(), "unknown")


# ──────────────────────────────────────────────
# Chrome Path
# ──────────────────────────────────────────────
def get_chrome_path(os_name):
    CHROME_PATHS = {
        "mac": [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ],
        "linux": [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
        ],
        "windows": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ],
    }

    for path in CHROME_PATHS.get(os_name, []):
        if os.path.exists(path):
            return path

    return None


# ──────────────────────────────────────────────
# Launch Chrome
# ──────────────────────────────────────────────
def launch_chrome():
    os_name = get_os()
    chrome_path = get_chrome_path(os_name)

    if not chrome_path:
        print(f"❌ Chrome not found on {os_name}")
        return None

    user_data_dir = os.path.join(os.path.expanduser("~"), "chrome_debug_profile")
    os.makedirs(user_data_dir, exist_ok=True)

    cmd = [
        chrome_path,
        "--remote-debugging-port=9222",
        "--remote-allow-origins=*",
        f"--user-data-dir={user_data_dir}",
    ]

    process = subprocess.Popen(cmd)
    print(f"✅ Chrome launched on {os_name}")
    return process


# ──────────────────────────────────────────────
# Verify Chrome Ready
# ──────────────────────────────────────────────
def verify_chrome(url="http://localhost:9222", max_try=10):
    version_url = f"{url}/json/version"
    for attempt in range(max_try):
        try:
            r = requests.get(version_url, timeout=2)
            if r.status_code == 200:
                print("✅ Chrome ready")
                return True
        except requests.RequestException:
            pass
        print(f"Waiting for Chrome... ({attempt + 1}/{max_try})")
        time.sleep(1)
    return False


# ──────────────────────────────────────────────
# ngrok Tunnel
# ──────────────────────────────────────────────
def create_tunnel():
    tunnel = ngrok.connect(9222, "tcp")
    print(f"✅ Tunnel created: {tunnel.public_url}")
    return tunnel.public_url


# ──────────────────────────────────────────────
# Register with Server
# ──────────────────────────────────────────────
def register_agent(tunnel_url, user_id):
    try:
        response = requests.post(
            f"{SERVER_URL}/api/agent/register",
            json={"user_id": user_id, "tunnel_url": tunnel_url},
            timeout=10,
        )
        data = response.json()
        print(f"✅ Registered with server: {data}")
        return True
    except Exception as e:
        print(f"❌ Failed to register with server: {e}")
        return False


# ──────────────────────────────────────────────
# Disconnect from Server
# ──────────────────────────────────────────────
def disconnect_agent(user_id):
    try:
        requests.delete(
            f"{SERVER_URL}/api/agent/disconnect/{user_id}",
            timeout=5,
        )
        print("✅ Disconnected from server")
    except Exception:
        pass


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main():
    print(f"Starting agent for user: {USER_ID}")
    print(f"Server: {SERVER_URL}")
    print(f"OS: {get_os()}")
    print("─" * 40)

    # Step 1 - Launch Chrome
    chrome = launch_chrome()
    if not chrome:
        print("❌ Could not find Chrome. Please install Google Chrome.")
        return

    # Step 2 - Wait for Chrome to be ready
    if not verify_chrome():
        print("❌ Chrome did not start in time.")
        chrome.terminate()
        return

    # Step 3 - Create ngrok tunnel
    tunnel_url = create_tunnel()

    # Step 4 - Register with server
    registered = register_agent(tunnel_url, USER_ID)
    if not registered:
        print("❌ Could not reach server. Is it running?")
        ngrok.disconnect(tunnel_url)
        chrome.terminate()
        return

    print("─" * 40)
    print("✅ Agent running. Browser is connected to server.")
    print("Press Ctrl+C to stop.")

    # Step 5 - Keep running
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nStopping agent...")
        disconnect_agent(USER_ID)
        ngrok.disconnect(tunnel_url)
        chrome.terminate()
        print("✅ Agent stopped")


if __name__ == "__main__":
    main()