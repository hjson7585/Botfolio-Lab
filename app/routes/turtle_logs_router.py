# app/routes/turtle_logs_router.py
import json
from fastapi import APIRouter

router = APIRouter()
LOG_FILE = "logs/turtle_logs.json"


@router.get("/turtle-logs")
def get_turtle_logs():
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []
