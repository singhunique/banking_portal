import os
import subprocess
import sys

def main():
    print("[+] Gisma B207 Automation Environment Launcher Engaged...")
    
    # 1. Automatically initialize database structure if missing
    if not os.path.exists('bank_system.db'):
        print("[*] Database not found. Initializing secure database schemas...")
        # If your initialization logic is inside db_init.py, run it:
        if os.path.exists('db_init.py'):
            subprocess.run([sys.executable, 'db_init.py'])
    else:
        print("[✓] Secure ledger database detected.")

    # 2. Fire up the central Flask application server
    print("[*] Spinning up local web application port node...")
    try:
        subprocess.run([sys.executable, 'app.py'])
    except KeyboardInterrupt:
        print("\n[-] Server session terminated gracefully.")

if __name__ == '__main__':
    main()