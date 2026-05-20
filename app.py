from flask import Flask, request, render_template, redirect, url_for, flash, session
import sqlite3
import werkzeug.security as ws
from datetime import datetime, timedelta
from crypto_utils import encrypt_balance, decrypt_balance, generate_transaction_mac, verify_transaction_mac

app = Flask(__name__)
# Secret key to sign Flask session cookies, preventing client-side tampering
app.secret_key = 'super-secure-flask-session-cookie-signing-key'

def get_db_connection():
    conn = sqlite3.connect('secure_bank.db')
    conn.row_factory = sqlite3.Row  # Access query results like dictionaries
    return conn

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Enforce basic password strength requirements as requested by the brief
        if len(password) < 8:
            flash("Security Policy Error: Password must be at least 8 characters long.")
            return redirect('/register')

        # Secure password storage using salted hashing (Argon2/pbkdf2 under the hood)
        hashed_password = ws.generate_password_hash(password)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # PARAMETERIZED QUERY: Neutralizes SQL injection vectors completely
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hashed_password))
            user_id = cursor.lastrowid
            
            # Initialize account balance securely at rest (\$1000 starting dummy balance)
            encrypted_bal = encrypt_balance(1000.0)
            cursor.execute("INSERT INTO accounts (user_id, encrypted_balance) VALUES (?, ?)", (user_id, encrypted_bal))
            
            conn.commit()
            flash("Registration successful! Please login.")
            return redirect('/')
        except sqlite3.IntegrityError:
            flash("Username already exists.")
        finally:
            conn.close()
            
    return render_template('register.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Secure parameterization
    cursor.execute("SELECT id, password_hash, failed_attempts, lockout_until FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    
    if not user:
        flash("Invalid authentication credentials.")
        return redirect('/')
        
    user_id, stored_hash, failed_attempts, lockout_until = user['id'], user['password_hash'], user['failed_attempts'], user['lockout_until']
    
    # Enforce Account Lockout Policy
    if lockout_until:
        if datetime.strptime(lockout_until, "%Y-%m-%d %H:%M:%S") > datetime.now():
            flash("Account is locked temporarily due to successive failures. Try again later.")
            conn.close()
            return redirect('/')
            
    # Cryptographic validation of password hash
    if ws.check_password_hash(stored_hash, password):
        # Reset counters on clean authenticated access
        cursor.execute("UPDATE users SET failed_attempts = 0, lockout_until = NULL WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        
        session['user_id'] = user_id
        session['username'] = username
        return redirect('/dashboard')
    else:
        new_attempts = failed_attempts + 1
        if new_attempts >= 3:
            # Apply 15 minute technical mitigation boundary
            lockout_time = (datetime.now() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("UPDATE users SET failed_attempts = ?, lockout_until = ? WHERE id = ?", (new_attempts, lockout_time, user_id))
        else:
            cursor.execute("UPDATE users SET failed_attempts = ? WHERE id = ?", (new_attempts, user_id))
        
        conn.commit()
        conn.close()
        flash("Invalid authentication credentials.")
        return redirect('/')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Retrieve user's balance information safely
    cursor.execute("SELECT encrypted_balance FROM accounts WHERE user_id = ?", (session['user_id'],))
    account = cursor.fetchone()
    balance = decrypt_balance(account['encrypted_balance'])
    
    # Retrieve complete transaction history
    cursor.execute("""
        SELECT t.*, u1.username as sender, u2.username as receiver 
        FROM transactions t
        JOIN users u1 ON t.sender_id = u1.id
        JOIN users u2 ON t.receiver_id = u2.id
        WHERE t.sender_id = ? OR t.receiver_id = ?
        ORDER BY t.timestamp DESC
    """, (session['user_id'], session['user_id']))
    tx_rows = cursor.fetchall()
    
    transactions = []
    for row in tx_rows:
        # Check validation logic to catch database level tampering
        is_valid = verify_transaction_mac(row['sender_id'], row['receiver_id'], row['amount'], row['hmac_signature'])
        transactions.append({
            'sender': row['sender'],
            'receiver': row['receiver'],
            'amount': row['amount'],
            'timestamp': row['timestamp'],
            'tampered': not is_valid  # If MAC check fails, warn UI!
        })
        
    conn.close()
    return render_template('dashboard.html', balance=balance, username=session['username'], transactions=transactions)

@app.route('/transfer', methods=['POST'])
def transfer():
    if 'user_id' not in session:
        return redirect('/')
        
    recipient_name = request.form['recipient']
    try:
        amount = float(request.form['amount'])
        if amount <= 0:
            raise ValueError()
    except ValueError:
        flash("Invalid financial amount specified.")
        return redirect('/dashboard')
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Look up recipient profile safely
    cursor.execute("SELECT id FROM users WHERE username = ?", (recipient_name,))
    recipient = cursor.fetchone()
    if not recipient:
        flash("Recipient user could not be found.")
        conn.close()
        return redirect('/dashboard')
        
    if recipient['id'] == session['user_id']:
        flash("You cannot issue fund transfers to your own account.")
        conn.close()
        return redirect('/dashboard')
        
    # 2. Check source user's capacity limits
    cursor.execute("SELECT encrypted_balance FROM accounts WHERE user_id = ?", (session['user_id'],))
    sender_account = cursor.fetchone()
    sender_balance = decrypt_balance(sender_account['encrypted_balance'])
    
    if sender_balance < amount:
        flash("Insufficient funds available to complete transaction.")
        conn.close()
        return redirect('/dashboard')
        
    # 3. Retrieve target user's capacity constraints
    cursor.execute("SELECT encrypted_balance FROM accounts WHERE user_id = ?", (recipient['id'],))
    rec_account = cursor.fetchone()
    rec_balance = decrypt_balance(rec_account['encrypted_balance'])
    
    # 4. Calculate new ledger balances and apply symmetric protection
    new_sender_bal = encrypt_balance(sender_balance - amount)
    new_rec_bal = encrypt_balance(rec_balance + amount)
    
    # 5. GENERATE DATA INTEGRITY MAC SIGNATURE FOR LEDGER ROW
    signature = generate_transaction_mac(session['user_id'], recipient['id'], amount)
    
    # 6. Execute atomic commit operations inside DB engine
    cursor.execute("UPDATE accounts SET encrypted_balance = ? WHERE user_id = ?", (new_sender_bal, session['user_id']))
    cursor.execute("UPDATE accounts SET encrypted_balance = ? WHERE user_id = ?", (new_rec_bal, recipient['id']))
    cursor.execute("INSERT INTO transactions (sender_id, receiver_id, amount, hmac_signature) VALUES (?, ?, ?, ?)",
                   (session['user_id'], recipient['id'], amount, signature))
                   
    conn.commit()
    conn.close()
    flash("Fund execution completed securely.")
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True, port=5000)