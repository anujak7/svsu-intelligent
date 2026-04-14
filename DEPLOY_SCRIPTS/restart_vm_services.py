import paramiko

user = "svsuuser"
pwd = "svsuindia@2026"
ip = "98.70.37.219"
remote_dir = "/home/svsuuser/svsu-intelligent"

def restart_services():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username=user, password=pwd)
    
    print("Stopping existing processes...")
    ssh.exec_command("pkill -9 -f api_server.py")
    ssh.exec_command("pkill -9 -f streamlit")
    
    import time
    time.sleep(2)
    
    print("Starting API Server...")
    ssh.exec_command(f"cd {remote_dir} && nohup ./venv/bin/python3 -u api_server.py > api.log 2>&1 &")
    
    print("Starting Streamlit App...")
    ssh.exec_command(f"cd {remote_dir} && nohup ./venv/bin/streamlit run app.py --server.port 8501 --server.address 0.0.0.0 > streamlit.log 2>&1 &")
    
    ssh.close()
    print("Restart commands sent.")

if __name__ == "__main__":
    restart_services()
