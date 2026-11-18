import os
import secrets
from pathlib import Path

# Project root = three levels up from this file (core → app → root)
BASE_DIR = Path(__file__).resolve().parents[2]

# Use the DATA_DIR environment variable if set, otherwise default to <root>/data
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))

RESTAURANTS_FILE = DATA_DIR / "restaurants.json"
MENU_ITEMS_FILE = DATA_DIR / "menu_items.json"
CUSTOMERS_FILE = DATA_DIR / "customers.json"
CARTS_FILE = DATA_DIR / "carts.json"
ORDERS_FILE = DATA_DIR / "orders.json"

# Key used to sign login tokens. Set the SECRET_KEY environment variable to keep tokens valid
# across restarts. It is never hard-coded: without the variable a random key is generated at
# startup, so every token simply stops working when the server restarts.
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)

# How long a login token stays valid
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
