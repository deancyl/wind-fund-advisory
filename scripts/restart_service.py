import os
import sys
import time
import socket
import subprocess
import urllib.request

def get_bindable_port():
    for p in [8501, 8585]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', p))
                return p
        except Exception:
            pass
    return 8585

target_port = get_bindable_port()
print(f"=== 1. Checking port {target_port} processes ===")
# 使用 netstat 查找监听 target_port 的 PID
res = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
pids_to_kill = set()
for line in res.stdout.splitlines():
    if f":{target_port}" in line and "LISTENING" in line:
        parts = line.strip().split()
        pid = parts[-1]
        if pid.isdigit() and int(pid) > 0:
            pids_to_kill.add(int(pid))

print(f"Found listening PIDs on {target_port}: {pids_to_kill}")
for pid in pids_to_kill:
    try:
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
        print(f"Terminated PID {pid}")
    except Exception as e:
        print(f"Error terminating PID {pid}: {e}")

def wait_for_port_free(port=target_port, timeout=10.0):
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
    print(f"Waiting for port {target_port} to be completely released...")
    if not wait_for_port_free(target_port, timeout=8.0):
        print(f"Warning: Port {target_port} did not release in time, continuing anyway.")
    else:
        print(f"Port {target_port} is now confirmed free.")
else:
    print(f"No existing process was listening on {target_port}.")

time.sleep(0.5)

print(f"=== 2. Launching Streamlit background daemon on port {target_port} ===")
# 使用 Windows 原生 CREATE_NO_WINDOW 后台拉起
CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008
python_exe = sys.executable
app_path = os.path.abspath("AGY2_FundAdvisory/app_gui.py")
os.makedirs("data", exist_ok=True)
log_file = open("data/streamlit_server.log", "w", encoding="utf-8")

cmd = [
    python_exe, "-m", "streamlit", "run", app_path,
    f"--server.port={target_port}",
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
health_url = f"http://127.0.0.1:{target_port}/_stcore/health"
ok = False
for attempt in range(25):
    time.sleep(1.0)
    try:
        req = urllib.request.Request(health_url)
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            if resp.status == 200:
                print(f"Attempt {attempt+1}: Streamlit health probe returned 200 OK on port {target_port}!")
                ok = True
                break
    except Exception as e:
        print(f"Attempt {attempt+1}: not ready yet ({e})")

if ok:
    print(f"SUCCESS: Streamlit daemon is healthy and running on port {target_port}!")
else:
    print(f"WARNING: Streamlit health check did not return 200 in 25 seconds.")

