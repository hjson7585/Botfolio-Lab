# app/routes/fox_logs_router.py
import json
from fastapi import APIRouter
from app.db.database import SessionLocal
from app.db.models import AgentLog

router = APIRouter()


@router.get("/fox-logs")
def get_fox_logs():
    """모멘텀여우(fox) 로그 — DB 기반, 전체 최신순"""
    db = SessionLocal()
    try:
        rows = (
            db.query(AgentLog)
            .filter(AgentLog.agent == "fox")
            .order_by(AgentLog.id.desc())
            .all()
        )
        result = []
        for row in rows:
            try:
                parsed = json.loads(row.data)
                parsed["_log_id"] = row.id
                result.append(parsed)
            except Exception:
                result.append(
                    {
                        "_log_id": row.id,
                        "raw": row.data[:200],
                        "status": "PARSE_ERROR",
                    }
                )
        return result
    except Exception as e:
        return [{"status": "DB_ERROR", "error": str(e)}]
    finally:
        db.close()
