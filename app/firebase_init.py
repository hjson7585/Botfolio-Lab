import os
from pathlib import Path
import firebase_admin
from firebase_admin import credentials

BASE_DIR = Path(__file__).resolve().parent.parent
FIREBASE_CRED_PATH = os.getenv(
    "FIREBASE_CREDENTIALS",
    str(BASE_DIR / "firebase-service-account.json")
)

if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_CRED_PATH)
    firebase_admin.initialize_app(cred)
