# app/routes/ai_logs_router.py
import json
from fastapi import APIRouter
from app.db.database import SessionLocal, DATABASE_URL
from app.db.models import AgentLog

router = APIRouter()


@router.get("/ai-logs")
def get_ai_logs():
    """최근 20개 bear 로그 반환 — 파싱 실패 행도 raw로 포함"""
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
                parsed = json.loads(row.data)
                parsed["_log_id"] = row.id
                result.append(parsed)
            except Exception:
                result.append(
                    {"_log_id": row.id, "raw": row.data[:200], "status": "PARSE_ERROR"}
                )
        return result
    except Exception as e:
        return [{"status": "DB_ERROR", "error": str(e)}]
    finally:
        db.close()


@router.get("/ai-logs/detail/{log_id}")
def get_ai_log_detail(log_id: int):
    """특정 로그 ID의 전체 내용 반환 (traceback 포함)"""
    db = SessionLocal()
    try:
        row = db.query(AgentLog).filter(AgentLog.id == log_id).first()
        if not row:
            return {"error": f"log_id={log_id} 없음"}
        try:
            parsed = json.loads(row.data)
            parsed["_log_id"] = row.id
            return parsed
        except Exception:
            return {"_log_id": row.id, "raw": row.data}
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


@router.get("/ai-logs/debug")
def debug_ai_logs():
    """DB 연결 상태 및 로그 개수 진단"""
    import traceback
    from app.db.database import engine
    from app.db.models import Base

    result = {
        "database_url_type": "postgresql" if "postgresql" in DATABASE_URL else "sqlite",
        "database_url_masked": (
            DATABASE_URL[:30] + "..." if len(DATABASE_URL) > 30 else DATABASE_URL
        ),
    }

    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
        result["table_create"] = "ok"
    except Exception as e:
        result["table_create"] = f"ERROR: {e}"

    try:
        db = SessionLocal()
        total = db.query(AgentLog).count()
        bear_total = db.query(AgentLog).filter(AgentLog.agent == "bear").count()
        # 최근 3개 로그 요약
        recent = (
            db.query(AgentLog)
            .filter(AgentLog.agent == "bear")
            .order_by(AgentLog.id.desc())
            .limit(3)
            .all()
        )
        db.close()
        result["total_logs"] = total
        result["bear_logs"] = bear_total
        result["recent_summaries"] = []
        for row in recent:
            try:
                d = json.loads(row.data)
                result["recent_summaries"].append(
                    {
                        "id": row.id,
                        "timestamp": d.get("timestamp"),
                        "status": d.get("status", d.get("action", "?")),
                        "note": d.get("note", "")[:80],
                    }
                )
            except Exception:
                result["recent_summaries"].append({"id": row.id, "raw": row.data[:80]})
    except Exception as e:
        result["db_query_error"] = traceback.format_exc()

    try:
        db = SessionLocal()
        test_entry = AgentLog(
            agent="bear",
            data=json.dumps(
                {
                    "agent": "인더스트리곰",
                    "status": "DEBUG_TEST",
                    "action": "DEBUG_TEST",
                    "note": "진단용 테스트 로그",
                },
                ensure_ascii=False,
            ),
        )
        db.add(test_entry)
        db.commit()
        db.refresh(test_entry)
        result["test_insert"] = f"ok — id={test_entry.id}"
        db.close()
    except Exception as e:
        result["test_insert"] = f"ERROR: {traceback.format_exc()}"

    return result
