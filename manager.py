import requests
import time
import subprocess
import urllib3
from datetime import datetime
# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def check_and_restart(url, process_name, timeout=5):
    try:
        response = requests.get(url, timeout=timeout, verify=False)
        if response.status_code == 200 and response.json().get('status') == 'healthy':
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"✓ [{current_time}] {url} healthy")
            return False
    except Exception as e:
        print(f"✗ {url} failed: {e}")

    print(f"Restarting {process_name}...")
    subprocess.run(["pkill", "-9", "-f", f"python3 {process_name}"])
    time.sleep(30)
    return True

while True:
    check_and_restart("http://127.0.0.1:80/health_check", "app.py")
    time.sleep(2)
    check_and_restart("https://127.0.0.1:443/health_check", "server.py")
    time.sleep(2)
    for i in range(16):
        sse_id = i+1
        check_and_restart(f"http://127.0.0.1:{5000+sse_id}/health_check", f"sse_server_backend{sse_id}.py")
        time.sleep(2)