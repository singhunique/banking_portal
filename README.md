# Secure Banking Portal Application

This repository contains an end-to-end secure banking portal built with Python, Flask, and SQLite for the Gisma individual course project. The system implements multi-factor authentication, cryptographic ledger signatures using HMAC-SHA256, symmetric data encryption at rest (Fernet), and active database tampering detection.

##  Automated Environment Setup

As required by the assignment guidelines, the environment initialization and execution are fully automated into a single  script. 

To install dependencies, generate local cryptographic keys, initialize the secure database structure, and start the local server web engine, run the following command in your terminal:

```bash
python run.py
