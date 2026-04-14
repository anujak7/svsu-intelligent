import paramiko
import os

user = "svsuuser"
pwd = "svsuindia@2026"
ip = "98.70.24.228"
remote_dir = "/home/svsuuser/svsu-intelligent"

# Folders to skip
SKIP_DIRS = ["node_modules", ".git", "__pycache__", "venv", ".vscode", ".gemini", ".agents"]

def upload_folder(sftp, local_root, remote_root):
    try:
        sftp.mkdir(remote_root)
        print(f"Created remote directory: {remote_root}")
    except:
        pass
        
    if not os.path.exists(local_root):
        return

    for item in os.listdir(local_root):
        if item in SKIP_DIRS:
            continue
            
        local_path = os.path.join(local_root, item)
        remote_path = f"{remote_root}/{item}"
        
        if os.path.isfile(local_path):
            print(f"Uploading file: {local_path} -> {remote_path}")
            sftp.put(local_path, remote_path)
        elif os.path.isdir(local_path):
            upload_folder(sftp, local_path, remote_path)

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to VM at {ip}...")
    try:
        ssh.connect(ip, username=user, password=pwd, timeout=10)
    except Exception as e:
        print(f"FAILED TO CONNECT: {e}")
        return
    
    sftp = ssh.open_sftp()
    
    # 1. Upload Unified Knowledge Base
    print("\nDeploying UNIFIED KNOWLEDGE BASE (SVSU_KNOWLEDGE)...")
    upload_folder(sftp, "SVSU_KNOWLEDGE", f"{remote_dir}/SVSU_KNOWLEDGE")
    
    # 2. Upload Backend Files
    print("\nDeploying Backend Core...")
    for f in ["api_server.py", "chatbot_engine.py"]:
        local_f = os.path.join("BOT_BACKEND", f)
        if os.path.exists(local_f):
            print(f"Uploading core file: {local_f}")
            sftp.put(local_f, f"{remote_dir}/{f}")

    # 3. Upload Deployment/Optimization Scripts
    print("\nDeploying Optimization Scripts...")
    for f in ["build_unified_knowledge.py", "sync_indexes.py"]:
        if os.path.exists(f):
            sftp.put(f, f"{remote_dir}/{f}")
            
    # 4. Upload Env Update
    if os.path.exists(".env"):
        sftp.put(".env", f"{remote_dir}/.env")
            
    sftp.close()
    
    # 5. Restart services
    print("\nRestarting Services on VM...")
    restart_cmd = f"cd {remote_dir} && pkill -f 'api_server.py' || true && nohup ./venv/bin/python3 -u api_server.py > api.log 2>&1 &"
    ssh.exec_command(restart_cmd)
    
    ssh.close()
    print("\n" + "="*40)
    print("DEPLOYMENT SUCCESSFUL!")
    print("="*40)
    print(f"Live API: http://{ip}:8000")
    print(f"Swagger Docs: http://{ip}:8000/docs")
    print(f"Widget Integration: http://{ip}:8000/assets/avatar.html")
    print("="*40)

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
