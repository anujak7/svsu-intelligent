import paramiko
import itertools

def test_ssh(user, pwd):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print(f"Testing {user} : {pwd} ...", end=" ", flush=True)
        ssh.connect('98.70.37.219', username=user, password=pwd, timeout=5)
        print("SUCCESS!")
        ssh.close()
        return True
    except Exception as e:
        print("Failed")
        return False

users = ["svsuuser", "svsuuserbot", "azureuser", "ubuntu"]
pwds = ["svsuindia2026", "svusindia2026"]

for u, p in itertools.product(users, pwds):
    if test_ssh(u, p):
        print(f"\nConnected successfully with: {u} / {p}")
        with open("found_creds.txt", "w") as f:
            f.write(f"{u}:{p}")
        break
else:
    print("\nNo combination worked.")
