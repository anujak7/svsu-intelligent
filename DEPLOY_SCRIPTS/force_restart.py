import paramiko

user = "svsuuser"
pwd  = "svsuindia@2026"
ip   = "98.70.24.228"
remote_dir = "/home/svsuuser/svsu-intelligent"

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username=user, password=pwd, timeout=10)
    
    # 1. Kill any process holding port 8000
    ssh.exec_command("sudo kill -9 $(sudo lsof -t -i:8000) 2>/dev/null || fuser -k 8000/tcp || true")
    
    # 2. Add an alternative kill process just in case
    ssh.exec_command("pkill -9 -f 'uvicorn' || pkill -9 -f 'api_server'")
    
    # 3. Wait for port release
    import time
    time.sleep(2)
    
    # 4. Start Server
    print("Starting server...")
    start_cmd = f"cd {remote_dir} && nohup ./venv/bin/python3 -m uvicorn api_server:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &"
    ssh.exec_command(start_cmd)
    
    time.sleep(3)
    _, out, _ = ssh.exec_command("ps aux | grep uvicorn | grep -v grep")
    print("running processes:", out.read().decode())

    ssh.close()

if __name__ == "__main__":
    main()
