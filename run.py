import os
import sys
import subprocess

def main():
    print("=== VaultGuard Academic Platform Launcher ===")

    try:
        from app import init_db
    except ImportError:
        print("\n[-] Error: Missing application components.")
        sys.exit(1)
    
    print("[*] Instantiating empty secure database schema...")
    init_db()
    print("[+] Complete. No mock records injected.")

    print("\n[+] Web server live. Booting microkernel framework...")
    subprocess.check_call([sys.executable, "-m", "flask", "run", "--port=5000"])

if __name__ == '__main__':
    main()