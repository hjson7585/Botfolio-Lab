import json

from fastapi import APIRouter

router = APIRouter()


LOG_FILE = "logs/ai_logs.json"


@router.get("/ai-logs")
def get_ai_logs():

    try:

        with open(LOG_FILE, "r", encoding="utf-8") as f:

            logs = json.load(f)

        return logs

    except Exception:

        return []
