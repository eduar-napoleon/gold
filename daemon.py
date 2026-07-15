import time
import subprocess
import os
import sys
from datetime import datetime

# Keep track of python executable in the venv
python_bin = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'venv', 'bin', 'python')
if not os.path.exists(python_bin):
    python_bin = sys.executable

sync_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sync.py')
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sync.log')

def log(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}\n"
    print(log_line, end="")
    try:
        with open(log_file, 'a') as f:
            f.write(log_line)
    except Exception as e:
        print(f"Failed to write log: {e}")

def run_sync():
    log("Starting scheduled synchronization...")
    try:
        process = subprocess.Popen(
            [python_bin, sync_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # Read output in real time
        for line in process.stdout:
            # write lines to log without repeating timestamp
            try:
                with open(log_file, 'a') as f:
                    f.write(line)
            except Exception:
                pass
                
        process.wait()
        if process.returncode == 0:
            log("Synchronization completed successfully.")
        else:
            log(f"Synchronization failed with exit code {process.returncode}.")
    except Exception as e:
        log(f"Error running sync script: {e}")

def main():
    log("Daemon started. Synchronization will run every hour.")
    # Run immediately on start
    run_sync()
    
    while True:
        log("Sleeping for 1 hour...")
        time.sleep(3600)
        run_sync()

if __name__ == '__main__':
    main()
