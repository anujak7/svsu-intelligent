import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('4.150.186.240', username='svsuuser', password='svsuindia@2026', timeout=8)

_, out, _ = ssh.exec_command('grep -rn "{content_html}" /home/svsuuser/svsu-intelligent/')
print(out.read().decode())
_, out, _ = ssh.exec_command('grep -rn "INDIA" /home/svsuuser/svsu-intelligent/ | head -n 10')
print(out.read().decode())
