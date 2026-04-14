import paramiko
import os

user = "svsuuser"
pwd = "svsuindia@2026"
ip = "98.70.37.219"
remote_dir = "/home/svsuuser/svsu-intelligent"

def upload_files():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username=user, password=pwd)
    
    sftp = ssh.open_sftp()
    
    files_to_upload = [
        "api_server.py",
        "app.py",
        "assets/avatar.html"
    ]
    
    for f in files_to_upload:
        local_path = f
        remote_path = f"{remote_dir}/{f}"
        print(f"Uploading {local_path} to {remote_path} ...")
        sftp.put(local_path, remote_path)
    
    sftp.close()
    ssh.close()
    print("Upload complete.")

if __name__ == "__main__":
    upload_files()
