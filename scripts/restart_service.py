import os
import sys
import time
import subprocess
import urllib.request

print("=== 1. Checking port 8501 processes ===")
# 使用 netstat 查找监听 8501 的 PID
res = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
pids_to_kill = set()
for line in res.stdout.splitlines():
    if ":8501" in line and "LISTENING" in line:
        parts = line.strip().split()
        pid = parts[-1]
        if pid.isdigit() and int(pid) > 0:
            pids_to_kill.add(int(pid))

print(f"Found listening PIDs on 8501: {pids_to_kill}")
for pid in pids_to_kill:
    try:
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
        print(f"Terminated PID {pid}")
    except Exception as e:
        print(f"Error terminating PID {pid}: {e}")

def wait_for_port_free(port=8501, timeout=10.0):
    start = time.time()
    while time.time() - start < timeout:
        res = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
        listening = False
        for line in res.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                listening = True
                break
        if not listening:
            return True
        time.sleep(0.5)
    return False

if pids_to_kill:
    print("Waiting for port 8501 to be completely released...")
    if not wait_for_port_free(8501, timeout=8.0):
        print("Warning: Port 8501 did not release in time, continuing anyway.")
    else:
        print("Port 8501 is now confirmed free.")
else:
    print("No existing process was listening on 8501.")

time.sleep(0.5)

print("=== 2. Launching Streamlit background daemon ===")
# 使用 Windows 原生 CREATE_NO_WINDOW 后台拉起
CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008
python_exe = sys.executable
app_path = os.path.abspath("AGY2_FundAdvisory/app_gui.py")
os.makedirs("data", exist_ok=True)
log_file = open("data/streamlit_server.log", "w", encoding="utf-8")

cmd = [
    python_exe, "-m", "streamlit", "run", app_path,
    "--server.port=8501",
    "--server.headless=true",
    "--server.address=0.0.0.0",
    "--browser.serverAddress=127.0.0.1"
]

proc = subprocess.Popen(
    cmd,
    creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS,
    stdout=log_file,
    stderr=log_file,
    close_fds=True,
    cwd=os.path.abspath(".")
)
print(f"Launched Streamlit daemon with PID {proc.pid}")

# 探活检测
print("=== 3. Health Probe (Waiting for HTTP 200) ===")
health_url = "http://127.0.0.1:8501/_stcore/health"
ok = False
for attempt in range(20):
    time.sleep(1.0)
    try:
        req = urllib.request.Request(health_url)
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            if resp.status == 200:
                print(f"Attempt {attempt+1}: Streamlit health probe returned 200 OK!")
                ok = True
                break
    except Exception as e:
        print(f"Attempt {attempt+1}: not ready yet ({e})")

if ok:
    print("SUCCESS: Streamlit daemon is healthy and running on port 8501!")
else:
    print("WARNING: Streamlit health check did not return 200 in 20 seconds.")

