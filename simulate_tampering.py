import sqlite3

def run_malicious_database_tampering():
    print("[ATTACK] Directly accessing 'secure_bank.db' file without backend authentication...")
    
    conn = sqlite3.connect('secure_bank.db')
    cursor = conn.cursor()
    
    # Target the last transaction row row and alter the amount field directly
    # This alters the data without regenerating the correct Server HMAC-SHA256 token!
    cursor.execute("SELECT transaction_id, amount FROM transactions ORDER BY transaction_id DESC LIMIT 1")
    row = cursor.fetchone()
    
    if not row:
        print("[CANCELLED] No transactions found in database. Please run app.py and make a money transfer first.")
        conn.close()
        return
        
    tx_id, old_amount = row
    new_amount = old_amount + 5000.0  # Artificially inject cash into the ledger item
    
    print(f"[ATTACK] Found Transaction ID {tx_id}. Modifying original amount ${old_amount} -> ${new_amount}...")
    
    cursor.execute("UPDATE transactions SET amount = ? WHERE transaction_id = ?", (new_amount, tx_id))
    conn.commit()
    conn.close()
    
    print("[SUCCESS] Database data successfully manipulated. Refresh your browser dashboard to witness the security framework identify the breach!")

if __name__ == "__main__":
    run_malicious_database_tampering()