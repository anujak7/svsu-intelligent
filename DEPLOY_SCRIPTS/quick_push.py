import paramiko
import os
import time

user = "svsuuser"
pwd  = "svsuindia@2026"
ip   = "4.150.186.240"
remote_dir = "/home/svsuuser/svsu-intelligent"
local_root = r"c:\Users\USER\Desktop\BOT-SVSU"

FILES_TO_DEPLOY = [
    ("admin_panel/chatbot.html", "admin_panel/chatbot.html"),
    ("admin_panel/admin_dashboard.html", "admin_panel/admin_dashboard.html"),
    ("admin_panel/admin.html", "admin_panel/admin.html"),
    ("assets/svsugirl.png", "assets/svsugirl.png"),
    ("assets/widget.js", "assets/widget.js"),
    ("BOT_BACKEND/api_server.py", "api_server.py"),
    ("BOT_BACKEND/agentic_system/domain_agents.py", "agentic_system/domain_agents.py"),
    ("SVSU_KNOWLEDGE/Structured_Data/official_admission_program_catalog_2025_26.json", "SVSU_KNOWLEDGE/Structured_Data/official_admission_program_catalog_2025_26.json"),
]

def main():
    print(f"Connecting to {ip}")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username=user, password=pwd, timeout=10)
    sftp = ssh.open_sftp()
    
    # Upload files
    for local_rel, remote_rel in FILES_TO_DEPLOY:
        local_path = os.path.join(local_root, local_rel)
        remote_path = f"{remote_dir}/{remote_rel}"
        if os.path.exists(local_path):
            print(f"Uploading {local_path} to {remote_path}")
            sftp.put(local_path, remote_path)
            print("OK")
    sftp.close()

    # Restart
    print("Restarting server...")
    _, out, err = ssh.exec_command(f"cd {remote_dir} && fuser -k 8000/tcp 2>/dev/null; pkill -f 'uvicorn' 2>/dev/null; pkill -f 'api_server' 2>/dev/null")
    time.sleep(2)
    start_cmd = f"cd {remote_dir} && nohup ./venv/bin/python3 -m uvicorn api_server:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &"
    ssh.exec_command(start_cmd)
    
    time.sleep(2)
    _, out, err = ssh.exec_command("ps aux | grep uvicorn | grep -v grep")
    result = out.read().decode()
    if result:
        print("Server is successfully running!")
        print(result.strip())
    else:
        print("Server failed to start!")
        _, out, err = ssh.exec_command(f"cat {remote_dir}/server.log | tail -n 20")
        print(out.read().decode())
        print(err.read().decode())

    ssh.close()

if __name__ == "__main__":
    main()
