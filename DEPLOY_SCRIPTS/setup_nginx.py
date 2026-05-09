import os
import subprocess

def run_cmd(cmd):
    print(f"Executing: {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def setup_nginx():
    # 1. Install Nginx
    run_cmd("sudo apt-get update")
    run_cmd("sudo apt-get install -y nginx")

    # 2. Chatbot Config
    chatbot_conf = """server {
    listen 80;
    server_name chatbot.svsu.ac.in;

    location / {
        proxy_pass http://127.0.0.1:8000/admin_panel/chatbot.html;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://127.0.0.1:8000/api;
        proxy_set_header Host $host;
    }

    location /assets {
        proxy_pass http://127.0.0.1:8000/assets;
        proxy_set_header Host $host;
    }

    location /admin_panel {
        proxy_pass http://127.0.0.1:8000/admin_panel;
        proxy_set_header Host $host;
    }
}
"""

    # 3. Admin Config
    admin_conf = """server {
    listen 80;
    server_name adminchatbot.svsu.ac.in;

    location / {
        proxy_pass http://127.0.0.1:8000/admin_panel/admin.html;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://127.0.0.1:8000/api;
        proxy_set_header Host $host;
    }

    location /assets {
        proxy_pass http://127.0.0.1:8000/assets;
        proxy_set_header Host $host;
    }

    location /admin_panel {
        proxy_pass http://127.0.0.1:8000/admin_panel;
        proxy_set_header Host $host;
    }
}
"""

    with open("chatbot_svsu", "w") as f:
        f.write(chatbot_conf)
    with open("adminchatbot_svsu", "w") as f:
        f.write(admin_conf)

    run_cmd("sudo mv chatbot_svsu /etc/nginx/sites-available/")
    run_cmd("sudo mv adminchatbot_svsu /etc/nginx/sites-available/")
    
    run_cmd("sudo ln -sf /etc/nginx/sites-available/chatbot_svsu /etc/nginx/sites-enabled/")
    run_cmd("sudo ln -sf /etc/nginx/sites-available/adminchatbot_svsu /etc/nginx/sites-enabled/")
    
    run_cmd("sudo rm -f /etc/nginx/sites-enabled/default")
    run_cmd("sudo nginx -t")
    run_cmd("sudo systemctl restart nginx")

    print("Nginx Setup Complete for chatbot.svsu.ac.in and adminchatbot.svsu.ac.in")

if __name__ == "__main__":
    setup_nginx()
