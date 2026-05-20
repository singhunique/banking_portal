import hmac
import hashlib
from cryptography.fernet import Fernet

# SYSTEM KEYS: In a production app, these would come from environment variables.
# For your assignment, hardcoding a static demonstration key ensures your professor can run it instantly.
SECRET_KEY = b'super-secret-system-key-keep-it-safe' 

# We generate a static Fernet key for database encryption demonstration
# To keep data readable across runs, we use a fixed valid Fernet key:
ENCRYPTION_KEY = b'vU8XvN_g1Z6W8z7X_Y4vN6B8o0L1z2X3Y4vN5B6o7L8='
cipher = Fernet(ENCRYPTION_KEY)

def encrypt_balance(balance_amount: float) -> str:
    """Encrypts the balance string so it is secure at rest in the database."""
    return cipher.encrypt(str(balance_amount).encode()).decode()

def decrypt_balance(encrypted_balance: str) -> float:
    """Decrypts the database balance back into a float for calculations."""
    return float(cipher.decrypt(encrypted_balance.encode()).decode())

def generate_transaction_mac(sender_id: int, receiver_id: int, amount: float) -> str:
    """
    Creates an immutable cryptographic signature for a transaction.
    This answers the brief: 'Who creates the signature?' -> The Backend Server.
    """
    message = f"{sender_id}:{receiver_id}:{amount}".encode()
    return hmac.new(SECRET_KEY, message, hashlib.sha256).hexdigest()

def verify_transaction_mac(sender_id: int, receiver_id: int, amount: float, stored_signature: str) -> bool:
    """
    Validates data integrity. If a malicious actor edits the DB file directly,
    the signature will fail to validate.
    """
    calculated_signature = generate_transaction_mac(sender_id, receiver_id, amount)
    return hmac.compare_digest(calculated_signature, stored_signature)