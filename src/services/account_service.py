import os
import json
from src.config.settings import ACCOUNTS_FILE

def load_accounts():
    """Loads accounts from the JSON file."""
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_accounts(accounts):
    """Saves accounts to the JSON file."""
    with open(ACCOUNTS_FILE, 'w') as f:
        json.dump(accounts, f, indent=4)
