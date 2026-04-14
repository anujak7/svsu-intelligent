import os
import subprocess
import paramiko
from datetime import datetime

# CONFIGURATION
VM_IP = '98.70.37.219'
VM_USER = 'svsuuser'
VM_PASS = 'svsuindia@2026'
BASE_PATH = '/home/svsuuser/svsu-intelligent'
LOCAL_INGEST_PATH = 'C:/Users/USER/Desktop/BOT-SVSU/CRAWLER/ingest.py'

def run_ingestion():
    """Runs the advanced ingestion locally once."""
    print(f"[{datetime.now()}] 🚀 Phase 1: Local Ingestion (Crawling website)...")
    try:
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
    print(f"[{datetime.now()}] 🔄 Phase 2: Uploading to VM...")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VM_IP, username=VM_USER, password=VM_PASS)
        
        sftp = ssh.open_sftp()
        
        # Pushing Database Files
        if os.path.exists('bm25_docs.pkl'):
            sftp.put('bm25_docs.pkl', f"{BASE_PATH}/bm25_docs.pkl")
            
        if os.path.exists('faiss_db'):
            try: sftp.mkdir(f"{BASE_PATH}/faiss_db")
            except: pass
            for file in os.listdir('faiss_db'):
                sftp.put(f"faiss_db/{file}", f"{BASE_PATH}/faiss_db/{file}")
        
        print("✅ VM Knowledge Base Updated.")
        
        # Restart server on VM
        ssh.exec_command(f'python3 {BASE_PATH}/start_vm_server.py')
        
        sftp.close()
        ssh.close()
        return True
    except Exception as e:
        print(f"❌ Sync Error: {e}")
        return False

if __name__ == "__main__":
    if run_ingestion():
        push_to_vm()
        print(f"✨ [DONE] SVSU Update Successful at {datetime.now()}")
    else:
        print("❌ Sync Failed. Check logs.")
