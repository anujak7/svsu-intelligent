import paramiko
import sys

def diagnose():
    host = "98.70.24.228"
    user = "svsuuser"
    pwd = "svsuindia@2026"
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=user, password=pwd)
        
        print("Checking API Server status...")
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep api_server.py | grep -v grep")
        print(f"Processes:\n{stdout.read().decode()}")
        
        print("Checking Python Packages...")
        stdin, stdout, stderr = ssh.exec_command("cd /home/svsuuser/svsu-intelligent && ./venv/bin/pip list | grep -E 'google-|groq|fastapi'")
        print(f"Packages:\n{stdout.read().decode()}")
        
        print("Final 50 lines of log:")
        stdin, stdout, stderr = ssh.exec_command("tail -n 50 /home/svsuuser/svsu-intelligent/final_server_log.txt")
        print(stdout.read().decode())
        
        print("Attempting Manual Start and capturing output for 10s...")
        stdin, stdout, stderr = ssh.exec_command("cd /home/svsuuser/svsu-intelligent && ./venv/bin/python3 api_server.py")
        
        # Give it a few seconds to crash
        import time
        time.sleep(5)
        
        # Read whatever is available
        print("--- STDOUT ---")
        print(stdout.read().decode())
        print("--- STDERR ---")
        print(stderr.read().decode())

        ssh.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    diagnose()
