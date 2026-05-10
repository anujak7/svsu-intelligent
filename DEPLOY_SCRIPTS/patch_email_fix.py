import paramiko
import time

# Try both known IPs
SERVERS = [
    {"ip": "4.150.186.240", "user": "svsuuser", "pwd": "svsuindia@2026"},
    {"ip": "98.70.24.228",  "user": "svsuuser", "pwd": "svsuindia@2026"},
]
REMOTE_DIR = "/home/svsuuser/svsu-intelligent"
LOCAL_API_SERVER = r"c:\Users\USER\Desktop\BOT-SVSU\BOT_BACKEND\api_server.py"
LOCAL_DOMAIN_AGENTS = r"c:\Users\USER\Desktop\BOT-SVSU\BOT_BACKEND\agentic_system\domain_agents.py"
LOCAL_CHATBOT_HTML = r"c:\Users\USER\Desktop\BOT-SVSU\admin_panel\chatbot.html"
LOCAL_ENV = r"c:\Users\USER\Desktop\BOT-SVSU\BOT_BACKEND\.env"
LOCAL_WIDGET_JS = r"c:\Users\USER\Desktop\BOT-SVSU\assets\widget.js"

def deploy_to(server):
    ip = server["ip"]
    print(f"\n=== Trying {ip} ===")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(ip, username=server["user"], password=server["pwd"], timeout=8)
    except Exception as e:
        print(f"  FAILED to connect: {e}")
        return False

    # 1. Upload files
    print("  Uploading fixed files...")
    sftp = ssh.open_sftp()
    sftp.put(LOCAL_API_SERVER, f"{REMOTE_DIR}/BOT_BACKEND/api_server.py")
    sftp.put(LOCAL_DOMAIN_AGENTS, f"{REMOTE_DIR}/BOT_BACKEND/agentic_system/domain_agents.py")
    sftp.put(LOCAL_CHATBOT_HTML, f"{REMOTE_DIR}/admin_panel/chatbot.html")
    sftp.put(LOCAL_ENV, f"{REMOTE_DIR}/BOT_BACKEND/.env")
    sftp.put(LOCAL_WIDGET_JS, f"{REMOTE_DIR}/assets/widget.js")
    sftp.close()
    print("  Upload complete!")

    # 3. Verify the fix landed
    _, out, _ = ssh.exec_command(rf"grep -n 'CONTENT_HTML\|content_html' {REMOTE_DIR}/BOT_BACKEND/api_server.py | head -10")
    result = out.read().decode().strip()
    print(f"  After upload placeholders:\n    {result}")

    # 4. Kill old server
    print("  Killing old server...")
    ssh.exec_command("fuser -k 8000/tcp 2>/dev/null; pkill -9 -f 'uvicorn' 2>/dev/null; pkill -9 -f 'api_server' 2>/dev/null")
    time.sleep(3)

    # 5. Start new server
    print("  Starting new server...")
    start_cmd = f"cd {REMOTE_DIR} && nohup ./venv/bin/python3 -m uvicorn BOT_BACKEND.api_server:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &"
    ssh.exec_command(start_cmd)
    time.sleep(4)

    # 6. Verify running
    _, out, _ = ssh.exec_command("ps aux | grep uvicorn | grep -v grep")
    running = out.read().decode().strip()
    if running:
        print(f"  ✅ Server running on {ip}!")
        print(f"  {running[:120]}")
    else:
        print(f"  ❌ Server not running! Checking logs...")
        _, out, _ = ssh.exec_command(f"tail -20 {REMOTE_DIR}/server.log")
        print(out.read().decode())

    ssh.close()
    return bool(running)

if __name__ == "__main__":
    for server in SERVERS:
        success = deploy_to(server)
        if success:
            print(f"\n✅ DEPLOYMENT SUCCESS on {server['ip']}")
