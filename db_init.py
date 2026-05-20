import sqlite3
from crypto_utils import encrypt_balance

def initialize_database():
    conn = sqlite3.connect('secure_bank.db')
    cursor = conn.cursor()

    print("Creating database tables...")

    # Users Table: Notice fields for Account Lockout policy
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        failed_attempts INTEGER DEFAULT 0,
        lockout_until TEXT
    )''')

    # Accounts Table: Balances are strings because they store ENCRYPTED text
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS accounts (
        account_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        encrypted_balance TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    # Transactions Table: Includes the HMAC signature field
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER,
        receiver_id INTEGER,
        amount REAL NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        hmac_signature TEXT NOT NULL
    )''')

    conn.commit()
    conn.close()
    print("Database initialization complete! 'secure_bank.db' created safely.")

if __name__ == '__main__':
    initialize_database()