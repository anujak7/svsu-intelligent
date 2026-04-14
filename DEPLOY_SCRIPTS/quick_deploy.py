import paramiko
import os
import time

user = "svsuuser"
pwd = "svsuindia@2026"
ip = "98.70.37.219"
remote_dir = "/home/svsuuser/svsu-intelligent"

def put(sftp, local, remote, retries=3):
    for i in range(retries):
        try:
            sftp.put(local, remote)
            size_kb = os.path.getsize(local) / 1024
            print(f"  ✓ {os.path.basename(local)} ({size_kb:.0f}KB)")
            return
        except Exception as e:
            print(f"  Retry {i+1}: {e}")
            time.sleep(2)

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username=user, password=pwd, timeout=30)
    sftp = ssh.open_sftp()

    print("Uploading files...")
    files = [
        ("admin_panel/talk.html",    f"{remote_dir}/admin_panel/talk.html"),
        ("assets/three.min.js",      f"{remote_dir}/assets/three.min.js"),
        ("assets/GLTFLoader.js",     f"{remote_dir}/assets/GLTFLoader.js"),
        ("assets/models/avatar.glb", f"{remote_dir}/assets/models/avatar.glb"),
        ("BOT_BACKEND/api_server.py",            f"{remote_dir}/api_server.py"),
    ]
    for local, remote in files:
        if os.path.exists(local):
            put(sftp, local, remote)
    
    sftp.close()

    print("\nRestarting server...")
    ssh.exec_command("pkill -f api_server || true; pkill -f uvicorn || true")
    time.sleep(2)
    ssh.exec_command(f"cd {remote_dir} && nohup python3 api_server.py > api.log 2>&1 &")
    time.sleep(2)

    _, out, _ = ssh.exec_command("ps aux | grep api_server | grep -v grep")
    running = out.read().decode().strip()
    ssh.close()

    print(f"\n{'✓ Server running!' if running else '✗ Check server manually'}")
    print(f"Visit: http://{ip}:8000")

if __name__ == "__main__":
    main()
