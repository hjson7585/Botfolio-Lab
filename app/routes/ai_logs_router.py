# app/routes/ai_logs_router.py
import json
from fastapi import APIRouter
from app.db.database import SessionLocal
from app.db.models import AgentLog

router = APIRouter()


@router.get("/ai-logs")
def get_ai_logs():
    db = SessionLocal()
    try:
        rows = (
            db.query(AgentLog)
            .filter(AgentLog.agent == "bear")
            .order_by(AgentLog.id.desc())
            .limit(20)
            .all()
        )
        result = []
        for row in rows:
            try:
                result.append(json.loads(row.data))
            except Exception:
                pass
        return result
    except Exception:
        return []
    finally:
        db.close()


@router.delete("/ai-logs")
def clear_ai_logs():
    db = SessionLocal()
    try:
        db.query(AgentLog).filter(AgentLog.agent == "bear").delete()
        db.commit()
        return {"ok": True, "message": "bear 로그 초기화 완료"}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()
