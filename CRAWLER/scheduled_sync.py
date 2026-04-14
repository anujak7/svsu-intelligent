import os
import time
import subprocess
import paramiko
from datetime import datetime

# CONFIGURATION
VM_IP = '98.70.37.219'
VM_USER = 'svsuuser'
VM_PASS = 'svsuindia@2026'
BASE_PATH = '/home/svsuuser/svsu-intelligent'
LOCAL_INGEST_PATH = 'C:/Users/USER/Desktop/BOT-SVSU/CRAWLER/ingest.py'
SYNC_INTERVAL = 3600  # 1 hour in seconds

def run_ingestion():
    """Runs the advanced ingestion locally."""
    print(f"[{datetime.now()}] 🚀 Initiating Broad Crawl...")
    try:
        # Run ingest.py as a subprocess
        result = subprocess.run(['python', LOCAL_INGEST_PATH], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Data Ingestion Complete.")
            return True
        else:
            print(f"❌ Ingestion Failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error during local ingestion: {e}")
        return False

def push_to_vm():
    """Pushes the updated FAISS and BM25 database to the VM."""
    print(f"[{datetime.now()}] 🔄 Syncing updated Knowledge Base to VM...")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VM_IP, username=VM_USER, password=VM_PASS)
        
        sftp = ssh.open_sftp()
        
        # 1. Pushing BM25 Index
        sftp.put('bm25_docs.pkl', f"{BASE_PATH}/bm25_docs.pkl")
        
        # 2. Pushing FAISS DB (Folder)
        if not os.path.exists('faiss_db'):
            print("⚠️ faiss_db folder not found locally. Skipping.")
        else:
            # Recreate faiss_db folder structure on VM if missing
            try: sftp.mkdir(f"{BASE_PATH}/faiss_db")
            except: pass
            
            for file in os.listdir('faiss_db'):
                sftp.put(f"faiss_db/{file}", f"{BASE_PATH}/faiss_db/{file}")
        
        print("✅ VM Sync Complete.")
        
        # 3. Restart Server to Load New Data
        print("🔄 Restarting Bot Engine on VM...")
        stdin, stdout, stderr = ssh.exec_command(f'python3 {BASE_PATH}/start_vm_server.py')
        time.sleep(2) # Buffer
        
        sftp.close()
        ssh.close()
        return True
    except Exception as e:
        print(f"❌ Error during VM Sync: {e}")
        return False

def main():
    print("🔥 SVSU INTELLIGENT - CONTINUOUS CRAWLER AGENT STARTED")
    print(f"Mode: Depth 10 Hybrid | Sync Interval: {SYNC_INTERVAL/60} mins")
    
    while True:
        success = run_ingestion()
        if success:
            push_to_vm()
            print(f"✨ Round Complete. Next update in {SYNC_INTERVAL/60} mins...")
        else:
            print("⚠️ Skipping VM sync due to local ingestion error.")
            
        time.sleep(SYNC_INTERVAL)

if __name__ == "__main__":
    main()
