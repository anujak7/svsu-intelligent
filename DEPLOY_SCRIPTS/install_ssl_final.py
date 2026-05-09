import os
import subprocess

def run_cmd(cmd):
    print(f"Executing: {cmd}")
    # Using -E to preserve environment if needed, but here simple sudo is fine
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(f"Error: {result.stderr}")
    return result.returncode

def install_ssl():
    # 1. Install Certbot
    run_cmd("sudo apt-get update")
    run_cmd("sudo apt-get install -y certbot python3-certbot-nginx")

    # 2. Obtain SSL Certificate
    # Note: This requires the domains to be already pointing to this server's IP
    # We use --redirect to automatically redirect HTTP to HTTPS
    cert_cmd = "sudo certbot --nginx -d chatbot.svsu.ac.in -d adminchatbot.svsu.ac.in --non-interactive --agree-tos --email anujak7@gmail.com --redirect"
    
    status = run_cmd(cert_cmd)
    
    if status == 0:
        print("SSL Certificate installed successfully!")
        run_cmd("sudo systemctl restart nginx")
    else:
        print("SSL Installation failed. Please check DNS propagation.")

if __name__ == "__main__":
    install_ssl()
