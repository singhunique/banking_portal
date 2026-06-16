import os
import sqlite3
import hmac
import hashlib
import re
import secrets
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(32))

DB_FILE = 'bank_system.db'

# --- CRYPTOGRAPHIC ENVIRONMENT ---
KEY_FILE = 'secret.key'
if not os.path.exists(KEY_FILE):
    fernet_key = Fernet.generate_key()
    with open(KEY_FILE, 'wb') as f:
        f.write(fernet_key)
else:
    with open(KEY_FILE, 'rb') as f:
        fernet_key = f.read()

cipher_suite = Fernet(fernet_key)
HMAC_SECRET = b'student_project_secure_hmac_key_2026'

# --- SECURITY resources
def validate_username(username):
    return re.match(r"^[a-zA-Z0-9_]{3,20}$", username)

def compute_tx_hmac(sender, receiver, encrypted_amount, timestamp):
    msg = f"{sender}|{receiver}|{encrypted_amount}|{timestamp}".encode('utf-8')
    return hmac.new(HMAC_SECRET, msg, hashlib.sha256).hexdigest()

def encrypt_data(data_str):
    return cipher_suite.encrypt(data_str.encode('utf-8')).decode('utf-8')

def decrypt_data(encrypted_str):
    try:
        return cipher_suite.decrypt(encrypted_str.encode('utf-8')).decode('utf-8')
    except Exception:
        return "DECRYPTION_FAILURE"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                encrypted_balance TEXT NOT NULL,
                failed_attempts INTEGER DEFAULT 0,
                locked_until TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                receiver TEXT NOT NULL,
                encrypted_amount TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                row_signature TEXT NOT NULL
            )
        ''')
        conn.commit()

# --- ROUTES ---

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not validate_username(username):
            flash("Username must be 3-20 alphanumeric characters.")
            return redirect(url_for('register'))

        if len(password) < 8 or not any(c.isdigit() for c in password) or not any(c.isupper() for c in password):
            flash("Password must be 8+ characters with 1 number and 1 uppercase letter.")
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password, method='scrypt')
        encrypted_initial_balance = encrypt_data("1000.00")

        try:
            with get_db_connection() as conn:
                conn.execute(
                    "INSERT INTO users (username, password_hash, encrypted_balance) VALUES (?, ?, ?)",
                    (username, hashed_pw, encrypted_initial_balance)
                )
                conn.commit()
        except sqlite3.IntegrityError:
          
            pass

     
        simple_pin = "".join([str(secrets.randbelow(10)) for _ in range(6)])
        
        session['mfa_pending_user'] = username
        session['mfa_correct_pin'] = simple_pin
        
        print("\n" + "="*50)
        print(f" [MFA SIMULATOR] Registration Pin for {username}: {simple_pin}")
        print("="*50 + "\n")
        
        return render_template('mfa.html', username=username)

    return render_template('register.html')
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    with get_db_connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

    if not user:
        flash("Invalid username or password.")
        return redirect(url_for('home'))

    if check_password_hash(user['password_hash'], password):
        simple_pin = "".join([str(secrets.randbelow(10)) for _ in range(6)])
        
        session['mfa_pending_user'] = username
        session['mfa_correct_pin'] = simple_pin
        
        print("\n" + "="*50)
        print(f" [MFA SIMULATOR] Verification Pin for {username}: {simple_pin}")
        print("="*50 + "\n")
        
        return render_template('mfa.html', username=username)
    else:
        flash("Invalid username or password.")
        return redirect(url_for('home'))

@app.route('/verify-mfa', methods=['POST'])
def verify_mfa():
    username = session.get('mfa_pending_user')
    correct_pin = session.get('mfa_correct_pin')
    user_input = request.form.get('mfa_code', '').strip()

    if not username or not correct_pin:
        return redirect(url_for('home'))

    if user_input == correct_pin:
        session.clear()
        session['username'] = username
        return redirect(url_for('dashboard'))
        
    flash("Incorrect 6-digit verification code.")
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('home'))
    
    username = session['username']
    with get_db_connection() as conn:
        user_row = conn.execute("SELECT encrypted_balance FROM users WHERE username = ?", (username,)).fetchone()
        tx_rows = conn.execute("SELECT * FROM transactions ORDER BY id DESC").fetchall()

    current_balance = float(decrypt_data(user_row['encrypted_balance']))
    
    processed_transactions = []
    for row in tx_rows:
        computed = compute_tx_hmac(row['sender'], row['receiver'], row['encrypted_amount'], row['timestamp'])
        tampered = not hmac.compare_digest(computed, row['row_signature'])
        decrypted_amount = decrypt_data(row['encrypted_amount'])
        
        processed_transactions.append({
            'sender': row['sender'],
            'receiver': row['receiver'],
            'amount': float(decrypted_amount) if decrypted_amount != "DECRYPTION_FAILURE" else 0.0,
            'timestamp': row['timestamp'],
            'tampered': tampered
        })

    return render_template('dashboard.html', username=username, balance=current_balance, transactions=processed_transactions)

@app.route('/transfer', methods=['POST'])
def transfer():
    if 'username' not in session:
        return redirect(url_for('home'))

    sender = session['username']
    
    # 1. Check if the user is submitting the 6-digit verification code
    tx_code_input = request.form.get('tx_code', '').strip()
    
    if tx_code_input:
        
        pending_tx = session.get('pending_tx')
        correct_tx_pin = session.get('pending_tx_pin')
        
        if not pending_tx or not correct_tx_pin:
            flash("Transaction expired or session lost. Please try again.")
            return redirect(url_for('dashboard'))
            
        if tx_code_input == correct_tx_pin:
           
            recipient = pending_tx['recipient']
            amount = pending_tx['amount']
            
            with get_db_connection() as conn:
                sender_row = conn.execute("SELECT encrypted_balance FROM users WHERE username = ?", (sender,)).fetchone()
                recipient_row = conn.execute("SELECT encrypted_balance FROM users WHERE username = ?", (recipient,)).fetchone()

                sender_bal = float(decrypt_data(sender_row['encrypted_balance']))
                recipient_bal = float(decrypt_data(recipient_row['encrypted_balance']))
                
                new_sender_enc = encrypt_data(f"{sender_bal - amount:.2f}")
                new_recipient_enc = encrypt_data(f"{recipient_bal + amount:.2f}")
                
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                encrypted_amount_str = encrypt_data(f"{amount:.2f}")
                row_signature = compute_tx_hmac(sender, recipient, encrypted_amount_str, timestamp)

                conn.execute("UPDATE users SET encrypted_balance = ? WHERE username = ?", (new_sender_enc, sender))
                conn.execute("UPDATE users SET encrypted_balance = ? WHERE username = ?", (new_recipient_enc, recipient))
                conn.execute(
                    "INSERT INTO transactions (sender, receiver, encrypted_amount, timestamp, row_signature) VALUES (?, ?, ?, ?, ?)",
                    (sender, recipient, encrypted_amount_str, timestamp, row_signature)
                )
                conn.commit()
                
            
            session.pop('pending_tx', None)
            session.pop('pending_tx_pin', None)
            
            flash("Transaction authorized and sent successfully!")
            return redirect(url_for('dashboard'))
        else:
            flash("Incorrect transaction code. Security lock engaged.")
            return redirect(url_for('dashboard'))

    # 2. First-time click: Get inputs, check balances, and generate terminal code
    recipient = request.form.get('recipient', '').strip()
    try:
        amount = float(request.form.get('amount', 0))
    except ValueError:
        flash("Invalid amount.")
        return redirect(url_for('dashboard'))

    if amount <= 0:
        flash("Amount must be greater than zero.")
        return redirect(url_for('dashboard'))

    if sender == recipient:
        flash("Cannot transfer money to yourself.")
        return redirect(url_for('dashboard'))

    with get_db_connection() as conn:
        sender_row = conn.execute("SELECT encrypted_balance FROM users WHERE username = ?", (sender,)).fetchone()
        recipient_row = conn.execute("SELECT encrypted_balance FROM users WHERE username = ?", (recipient,)).fetchone()

        if not recipient_row:
            flash("Recipient user account not found.")
            return redirect(url_for('dashboard'))

        sender_bal = float(decrypt_data(sender_row['encrypted_balance']))
        if sender_bal < amount:
            flash("Insufficient funds.")
            return redirect(url_for('dashboard'))


    tx_pin = "".join([str(secrets.randbelow(10)) for _ in range(6)])
    
   
    session['pending_tx'] = {'recipient': recipient, 'amount': amount}
    session['pending_tx_pin'] = tx_pin
    
    
    print("\n" + "!"*60)
    print(f" [TRANSACTION GUARD] Action requested by {sender}")
    print(f" Sending: ${amount:.2f} to -> {recipient}")
    print(f" ENTER CODE TO CONFIRM SECURITY AUTHORIZATION: {tx_pin}")
    print("!"*60 + "\n")
    
    
    session['show_tx_verification'] = True
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)