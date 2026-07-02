# app/routes/fox_logs_router.py
import json
from fastapi import APIRouter

router = APIRouter()
LOG_FILE = "logs/fox_logs.json"


@router.get("/fox-logs")
def get_fox_logs():
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []
