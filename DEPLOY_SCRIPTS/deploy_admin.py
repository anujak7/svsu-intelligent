import paramiko
import os

user = "svsuuser"
pwd = "svsuindia@2026"
ip = "98.70.37.219"
remote_dir = "/home/svsuuser/svsu-intelligent"

def upload_admin_panel():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username=user, password=pwd)
    
    sftp = ssh.open_sftp()
    
    local_admin_dir = "admin_panel"
    remote_admin_dir = f"{remote_dir}/admin_panel"
    
    # Try creating remote dir just in case
    try:
        sftp.mkdir(remote_admin_dir)
    except:
        pass
        
    for f in os.listdir(local_admin_dir):
        if os.path.isfile(os.path.join(local_admin_dir, f)):
            local_path = os.path.join(local_admin_dir, f)
            remote_path = f"{remote_admin_dir}/{f}"
            print(f"Uploading {local_path} to {remote_path} ...")
            sftp.put(local_path, remote_path)
    
    sftp.close()
    ssh.close()
    print("Admin panel upload complete.")

if __name__ == "__main__":
    upload_admin_panel()
