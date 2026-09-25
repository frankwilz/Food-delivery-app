import os
from pathlib import Path

# Project root = three levels up from this file (core → app → root)
BASE_DIR = Path(__file__).resolve().parents[2]

# Use the DATA_DIR environment variable if set, otherwise default to <root>/data
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))

RESTAURANTS_FILE = DATA_DIR / "restaurants.json"