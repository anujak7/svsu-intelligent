import paramiko
import os

user = "svsuuser"
pwd  = "svsuindia@2026"
ip   = "4.150.186.240"
remote_dir = "/home/svsuuser/svsu-intelligent"
local_file = r"c:\Users\USER\Desktop\BOT-SVSU\DEPLOY_SCRIPTS\setup_nginx.py"
remote_file = "/home/svsuuser/svsu-intelligent/setup_nginx.py"

def main():
    print(f"Connecting to {ip}")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username=user, password=pwd, timeout=10)
    
    sftp = ssh.open_sftp()
    print(f"Uploading setup script...")
    sftp.put(local_file, remote_file)
    sftp.close()

    print("Running Nginx Setup on VM...")
    # Using sudo with -S to pass password if needed, but here we assume user has sudo or no-password sudo
    stdin, stdout, stderr = ssh.exec_command(f"python3 {remote_file}")
    
    # Wait for completion
    exit_status = stdout.channel.recv_exit_status()
    print(stdout.read().decode())
    print(stderr.read().decode())
    
    if exit_status == 0:
        print("Nginx Setup Execution SUCCESS")
    else:
        print(f"Nginx Setup Execution FAILED with exit status {exit_status}")

    ssh.close()

if __name__ == "__main__":
    main()
