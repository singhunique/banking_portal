import sqlite3

def run_malicious_database_tampering():
    print("[ATTACK] Accessing 'bank_system.db' directly...")
    
    # Open the correct database file name
    conn = sqlite3.connect('bank_system.db')
    cursor = conn.cursor()
    
    # 1. Target the last transaction row using the correct column name
    cursor.execute("SELECT id, encrypted_amount FROM transactions ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    
    if not row:
        print("[CANCELLED] No transactions found. Run app.py and make a money transfer first.")
        conn.close()
        return
        
    tx_id, old_encrypted_amount = row
    
    # 2. Inject a completely random encrypted token string to fake a balance value modification
    # This represents an attacker replacing data without knowing the HMAC secret key
    fake_encrypted_amount = "gAAAAABm_FakeCiphertextStringHereValueRefusedByHMAC="
    
    print(f"[ATTACK] Found Transaction ID {tx_id}. Overwriting encrypted data column...")
    
    # 3. Update using the correct schema definitions
    cursor.execute("UPDATE transactions SET encrypted_amount = ? WHERE id = ?", (fake_encrypted_amount, tx_id))
    conn.commit()
    conn.close()
    
    print("[SUCCESS] Database row manipulated. Refresh your dashboard browser tab to view the alert!")

if __name__ == "__main__":
    run_malicious_database_tampering()