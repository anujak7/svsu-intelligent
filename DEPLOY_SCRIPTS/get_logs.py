import paramiko

user = "svsuuser"
pwd  = "svsuindia@2026"
ip   = "4.150.186.240"
remote_dir = "/home/svsuuser/svsu-intelligent"

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username=user, password=pwd, timeout=10)
    
    _, out, err = ssh.exec_command(f"tail -n 1000 {remote_dir}/server.log")
    log_data = out.read().decode()
    ssh.close()
    
    print("--- SCANNING LAST 1000 LINES ---")
    lines = log_data.split('\n')
    for i, line in enumerate(lines):
        if any(kw in line for kw in ["ERROR", "Exception", "Traceback", "TypeError", "AttributeError", "KeyError", " 500 "]):
            print(f"L{i}: {line}")
            # print context
            for j in range(max(0, i-5), min(len(lines), i+15)):
                if j != i: print(f"  {j}: {lines[j]}")
            print("-" * 50)

if __name__ == "__main__":
    main()
