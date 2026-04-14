import paramiko
import os

user = "svsuuser"
pwd = "svsuindia@2026"
ip = "98.70.37.219"
remote_dir = "/home/svsuuser/svsu-intelligent"

def upload_folder(sftp, local_root, remote_root):
    # Try creating remote dir
    try:
        sftp.mkdir(remote_root)
        print(f"Created remote directory: {remote_root}")
    except:
        pass
        
    for item in os.listdir(local_root):
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
    ssh.connect(ip, username=user, password=pwd)
    
    sftp = ssh.open_sftp()
    
    # Upload Assets (including models)
    upload_folder(sftp, "assets", f"{remote_dir}/assets")
    
    # Upload Data folder (if exists)
    if os.path.exists("data"):
        upload_folder(sftp, "data", f"{remote_dir}/data")

    # Upload core scripts
    for f in ["api_server.py", "chatbot_engine.py", "core_facts.txt", ".env"]:
        if os.path.exists(f):
            print(f"Uploading core file: {f}")
            sftp.put(f, f"{remote_dir}/{f}")
    
    sftp.close()
    ssh.close()
    print("Asset and Core deployment complete.")

if __name__ == "__main__":
    main()
