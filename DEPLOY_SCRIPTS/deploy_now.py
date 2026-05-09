import paramiko
import os
import time

user = "svsuuser"
pwd  = "svsuindia@2026"
ip   = "4.150.186.240"
remote_dir = "/home/svsuuser/svsu-intelligent"
local_root = r"c:\Users\USER\Desktop\BOT-SVSU"

FILES_TO_DEPLOY = [
    # (local_relative_path, remote_relative_path)
    ("admin_panel/chatbot.html",                          "admin_panel/chatbot.html"),
    ("assets/widget.js",                                  "assets/widget.js"),
    ("BOT_BACKEND/api_server.py",                         "api_server.py"),
    ("BOT_BACKEND/agentic_system/domain_agents.py",       "agentic_system/domain_agents.py"),
    ("SVSU_KNOWLEDGE/Structured_Data/official_admission_program_catalog_2025_26.json", "SVSU_KNOWLEDGE/Structured_Data/official_admission_program_catalog_2025_26.json"),
]

def put_file(sftp, local_path, remote_path, retries=3):
    for i in range(retries):
        try:
            sftp.put(local_path, remote_path)
            size_kb = os.path.getsize(local_path) / 1024
            print(f"  ✓  {os.path.basename(local_path)} ({size_kb:.1f} KB)")
            return True
        except Exception as e:
            print(f"  ✗  Retry {i+1}/3 — {e}")
            time.sleep(2)
    return False

def run_cmd(ssh, cmd, label=""):
    _, out, err = ssh.exec_command(cmd)
    stdout = out.read().decode().strip()
    stderr = err.read().decode().strip()
    if label:
        print(f"\n[{label}]")
    if stdout: print(stdout)
    if stderr: print(f"STDERR: {stderr}")
    return stdout

def main():
    print(f"\n{'='*50}")
    print(f"  SVSU Intelligent — Direct VM Deploy")
    print(f"  Target: {user}@{ip}:{remote_dir}")
    print(f"{'='*50}\n")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("Connecting to VM...")
    ssh.connect(ip, username=user, password=pwd, timeout=30)
    print("✓ Connected!\n")

    sftp = ssh.open_sftp()

    print("Uploading changed files:")
    all_ok = True
    for local_rel, remote_rel in FILES_TO_DEPLOY:
        local_path  = os.path.join(local_root, local_rel)
        remote_path = f"{remote_dir}/{remote_rel}"
        if not os.path.exists(local_path):
            print(f"  ⚠  Skipped (not found locally): {local_rel}")
            continue
        ok = put_file(sftp, local_path, remote_path)
        if not ok:
            all_ok = False

    sftp.close()

    if not all_ok:
        print("\n⚠ Some files failed to upload. Check errors above.")

    # Rebuild knowledge store on VM
    print("\nRebuilding knowledge store on VM...")
    rebuild_cmd = (
        f"cd {remote_dir} && "
        "./venv/bin/python3 -c \""
        "import sys; sys.path.insert(0, 'BOT_BACKEND'); "
        "from agentic_system.knowledge_store import ensure_knowledge_store_ready; "
        "r = ensure_knowledge_store_ready(force=True); "
        "print(f'DB rebuild: {r[\\\"status\\\"]}, chunks={r[\\\"chunks\\\"]}'); "
        "\""
    )
    run_cmd(ssh, rebuild_cmd, "KB Rebuild")

    # Restart the FastAPI server
    print("\nRestarting FastAPI server...")
    run_cmd(ssh, "pkill -f 'uvicorn' 2>/dev/null; pkill -f 'api_server' 2>/dev/null; sleep 2", "Kill old server")
    
    start_cmd = (
        f"cd {remote_dir} && "
        "nohup ./venv/bin/python3 -m uvicorn BOT_BACKEND.api_server:app --host 0.0.0.0 --port 8000 "
        "> server.log 2>&1 &"
    )
    run_cmd(ssh, start_cmd, "Start server")
    time.sleep(3)

    # Verify
    check = run_cmd(ssh, "ps aux | grep uvicorn | grep -v grep | head -2", "Process check")
    if check:
        print(f"\n✓ Server is RUNNING!")
    else:
        # Try alternate start
        run_cmd(ssh, f"cd {remote_dir} && nohup ./venv/bin/python3 api_server.py > server.log 2>&1 &", "Alt start")
        time.sleep(3)
        check2 = run_cmd(ssh, "ps aux | grep api_server | grep -v grep | head -2", "Alt check")
        if check2:
            print(f"\n✓ Server is RUNNING (alt mode)!")
        else:
            print(f"\n✗ Server may not be running. Check: ssh {user}@{ip} 'cat {remote_dir}/server.log'")

    print(f"\n  Live URL: http://{ip}:8000")
    print("="*50)
    ssh.close()

if __name__ == "__main__":
    main()
