import os
import sys
import subprocess
import sqlite3

def run_automation_pipeline():
    print("=" * 60)
    print("   SECURE BANKING PORTAL - AUTOMATED DEPLOYMENT ORCHESTRATOR")
    print("=" * 60)

    # 1. Install required security dependencies from manifest
    print("\n[STEP 1] Verifying and installing system dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("[SUCCESS] Dependencies configured correctly.")
    except Exception as e:
        print(f"[ERROR] Dependency installation failed: {e}")
        sys.exit(1)

    # 2. Automatically invoke database migrations/schema structure setup
    print("\n[STEP 2] Verifying database structure...")
    if not os.path.exists("secure_bank.db"):
        print("[INFO] 'secure_bank.db' not found. Executing fresh initialization...")
        try:
            from db_init import initialize_database
            initialize_database()
            print("[SUCCESS] Database tables created safely.")
        except ImportError:
            print("[ERROR] Could not locate 'db_init.py'. Please check folder integrity.")
            sys.exit(1)
    else:
        print("[INFO] Existing database 'secure_bank.db' recognized. Skipping re-initialization.")

    # 3. Boot up core web gateway server instance
    print("\n[STEP 3] Launching production development environment gateway...")
    print("=" * 60)
    print("  The Secure Banking Portal is now loading.")
    print("  Please open your browser and navigate to: http://127.0.0.1:5000")
    print("=" * 60 + "\n")
    
    try:
        subprocess.run([sys.executable, "app.py"], check=True)
    except KeyboardInterrupt:
        print("\n[INFO] Server stopped manually via user interrupt. Exiting execution safely.")

if __name__ == "__main__":
    run_automation_pipeline()