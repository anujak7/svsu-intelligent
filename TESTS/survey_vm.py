import paramiko
import os

user = "svsuuser"
pwd = "svsuindia@2026"
ip = "98.70.37.219"

def run_remote(cmd):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username=user, password=pwd)
    stdin, stdout, stderr = ssh.exec_command(cmd)
    res = stdout.read().decode()
    err = stderr.read().decode()
    ssh.close()
    return res, err

print("--- Listing home directory ---")
print(run_remote("ls -F")[0])

print("--- Checking svsu-intelligent directory ---")
print(run_remote("ls -F ~/svsu-intelligent")[0])
