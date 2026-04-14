import paramiko

user = "svsuuser"
pwd = "svsuindia@2026"
ip = "98.70.37.219"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(ip, username=user, password=pwd)

# Add API_HOST to .env if not present
cmd = "grep -q 'API_HOST' ~/svsu-intelligent/.env || echo 'API_HOST=http://98.70.37.219:8000' >> ~/svsu-intelligent/.env"
ssh.exec_command(cmd)

ssh.close()
print("Config updated on VM.")
