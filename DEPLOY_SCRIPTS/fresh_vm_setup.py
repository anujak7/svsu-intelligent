import paramiko
import os
import time

# VM Configuration
IP = "4.150.186.240"
PWD = "svsuindia@2026"
USERS_TO_TRY = ["svsu-azureuser", "svsuuser", "azureuser"]
REMOTE_DIR = "/home/{user}/svsu-intelligent"
LOCAL_ROOT = r"c:\Users\USER\Desktop\BOT-SVSU"

# Skip directories
SKIP_DIRS = ["node_modules", ".git", "__pycache__", "venv", ".vscode", ".gemini", ".agents", "model_cache"]

def run_remote_cmd(ssh, cmd, description):
    print(f"\n>>> Running: {description}")
    _, out, err = ssh.exec_command(cmd)
    stdout = out.read().decode().strip()
    stderr = err.read().decode().strip()
    if stdout: print(f"STDOUT: {stdout}")
    if stderr: print(f"STDERR: {stderr}")
    return stdout, stderr

def upload_folder_recursive(sftp, local_path, remote_path):
    try:
        sftp.mkdir(remote_path)
    except:
        pass

    for item in os.listdir(local_path):
        if item in SKIP_DIRS:
            continue
        
        l_path = os.path.join(local_path, item)
        r_path = f"{remote_path}/{item}"
        
        if os.path.isfile(l_path):
            print(f"Uploading: {l_path} -> {r_path}")
            sftp.put(l_path, r_path)
        elif os.path.isdir(l_path):
            upload_folder_recursive(sftp, l_path, r_path)

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    connected_user = None
    for user in USERS_TO_TRY:
        print(f"Trying connection as {user}@{IP}...")
        try:
            ssh.connect(IP, username=user, password=PWD, timeout=10)
            print(f"Connected successfully as {user}!")
            connected_user = user
            break
        except Exception as e:
            print(f"Failed as {user}: {e}")

    if not connected_user:
        print("Could not connect with any known username. Please verify VM username and password.")
        return

    R_DIR = REMOTE_DIR.format(user=connected_user)

    # 1. Prepare Environment
    run_remote_cmd(ssh, f"mkdir -p {R_DIR}", "Create project directory")
    # Using sudo might prompt for password, let's hope it's passwordless or same password
    run_remote_cmd(ssh, f"echo '{PWD}' | sudo -S apt-get update", "Update apt")
    run_remote_cmd(ssh, f"echo '{PWD}' | sudo -S apt-get install -y python3-venv python3-pip libgl1 libglib2.0-0", "Install system dependencies")

    # 2. Upload Files
    sftp = ssh.open_sftp()
    print("\nStarting recursive upload...")
    for folder in ["admin_panel", "assets", "BOT_BACKEND", "SVSU_KNOWLEDGE"]:
        l_f = os.path.join(LOCAL_ROOT, folder)
        if os.path.exists(l_f):
            upload_folder_recursive(sftp, l_f, f"{R_DIR}/{folder}")
    
    for f in [".env", "requirements.txt"]:
        l_f = os.path.join(LOCAL_ROOT, f)
        if not os.path.exists(l_f) and f == "requirements.txt":
            l_f = os.path.join(LOCAL_ROOT, "BOT_BACKEND", "requirements.txt")
            
        if os.path.exists(l_f):
            sftp.put(l_f, f"{R_DIR}/{f}")
    
    sftp.close()

    # 3. Setup Virtual Environment
    run_remote_cmd(ssh, f"cd {R_DIR} && python3 -m venv venv", "Create virtual environment")
    run_remote_cmd(ssh, f"cd {R_DIR} && ./venv/bin/pip install --upgrade pip", "Upgrade pip")
    run_remote_cmd(ssh, f"cd {R_DIR} && ./venv/bin/pip install -r requirements.txt", "Install requirements")

    # 4. Sync Structure (Move files out of BOT_BACKEND to root for easy execution)
    run_remote_cmd(ssh, f"cd {R_DIR} && cp BOT_BACKEND/*.py . && cp -r BOT_BACKEND/agentic_system .", "Sync structure")

    # 5. Start Server
    print("\nStarting the server...")
    run_remote_cmd(ssh, "pkill -f 'uvicorn' || true", "Kill old processes")
    # Start on 0.0.0.0 so it's accessible externally
    start_cmd = f"cd {R_DIR} && nohup ./venv/bin/python3 -m uvicorn api_server:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &"
    ssh.exec_command(start_cmd)
    
    time.sleep(5)
    print("\n" + "="*50)
    print("DEPLOYMENT COMPLETE!")
    print("="*50)
    print(f"Chatbot URL: http://{IP}:8000/admin_panel/chatbot.html")
    print(f"Admin Panel: http://{IP}:8000/admin_panel/admin.html")
    print("="*50)
    
    ssh.close()

if __name__ == "__main__":
    main()
