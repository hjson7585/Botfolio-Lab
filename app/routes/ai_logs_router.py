# app/routes/ai_logs_router.py
import json
from fastapi import APIRouter
from app.db.database import SessionLocal, DATABASE_URL
from app.db.models import AgentLog

router = APIRouter()

# ── 에이전트별 로그 조회 ──────────────────────────────────


@router.get("/ai-logs")
def get_ai_logs():
    """인더스트리곰(bear) 전체 로그 — 최신순, 한도 없음"""
    return _get_logs_by_agent("bear")


@router.get("/ai-logs/fox")
def get_fox_ai_logs():
    """모멘텀여우(fox) 전체 로그 — 최신순, 한도 없음"""
    return _get_logs_by_agent("fox")


@router.get("/ai-logs/turtle")
def get_turtle_ai_logs():
    """배당거북(turtle) 전체 로그 — 최신순, 한도 없음"""
    return _get_logs_by_agent("turtle")


@router.get("/ai-logs/all")
def get_all_ai_logs():
    """전체 에이전트 로그 — 최신순, 한도 없음"""
    db = SessionLocal()
    try:
        rows = db.query(AgentLog).order_by(AgentLog.id.desc()).all()
        return _parse_rows(rows)
    except Exception as e:
        return [{"status": "DB_ERROR", "error": str(e)}]
    finally:
        db.close()


def _get_logs_by_agent(agent: str) -> list:
    db = SessionLocal()
    try:
        rows = (
            db.query(AgentLog)
            .filter(AgentLog.agent == agent)
            .order_by(AgentLog.id.desc())
            .all()
        )
        return _parse_rows(rows)
    except Exception as e:
        return [{"status": "DB_ERROR", "error": str(e)}]
    finally:
        db.close()


def _parse_rows(rows) -> list:
    result = []
    for row in rows:
        try:
            parsed = json.loads(row.data)
            parsed["_log_id"] = row.id
            parsed["_agent"] = row.agent
            result.append(parsed)
        except Exception:
            result.append(
                {
                    "_log_id": row.id,
                    "_agent": row.agent,
                    "raw": row.data[:200],
                    "status": "PARSE_ERROR",
                }
            )
    return result


# ── 특정 로그 상세 조회 ──────────────────────────────────


@router.get("/ai-logs/detail/{log_id}")
def get_ai_log_detail(log_id: int):
    """특정 로그 ID 전체 내용 반환 (traceback 포함)"""
    db = SessionLocal()
    try:
        row = db.query(AgentLog).filter(AgentLog.id == log_id).first()
        if not row:
            return {"error": f"log_id={log_id} 없음"}
        try:
            parsed = json.loads(row.data)
            parsed["_log_id"] = row.id
            parsed["_agent"] = row.agent
            return parsed
        except Exception:
            return {"_log_id": row.id, "_agent": row.agent, "raw": row.data}
    finally:
        db.close()


# ── 로그 삭제 ──────────────────────────────────────────


@router.delete("/ai-logs")
def clear_ai_logs():
    """인더스트리곰(bear) 로그 전체 삭제"""
    return _clear_logs_by_agent("bear")


@router.delete("/ai-logs/fox")
def clear_fox_ai_logs():
    """모멘텀여우(fox) 로그 전체 삭제"""
    return _clear_logs_by_agent("fox")


@router.delete("/ai-logs/turtle")
def clear_turtle_ai_logs():
    """배당거북(turtle) 로그 전체 삭제"""
    return _clear_logs_by_agent("turtle")


@router.delete("/ai-logs/all")
def clear_all_ai_logs():
    """전체 에이전트 로그 삭제"""
    db = SessionLocal()
    try:
        db.query(AgentLog).delete()
        db.commit()
        return {"ok": True, "message": "전체 에이전트 로그 삭제 완료"}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


def _clear_logs_by_agent(agent: str) -> dict:
    db = SessionLocal()
    try:
        db.query(AgentLog).filter(AgentLog.agent == agent).delete()
        db.commit()
        return {"ok": True, "message": f"{agent} 로그 삭제 완료"}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


# ── 진단 ──────────────────────────────────────────────


@router.get("/ai-logs/debug")
def debug_ai_logs():
    """DB 연결 상태 및 에이전트별 로그 개수 진단"""
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
        result["log_counts"] = {
            "bear": db.query(AgentLog).filter(AgentLog.agent == "bear").count(),
            "fox": db.query(AgentLog).filter(AgentLog.agent == "fox").count(),
            "turtle": db.query(AgentLog).filter(AgentLog.agent == "turtle").count(),
            "total": db.query(AgentLog).count(),
        }
        # 에이전트별 최근 1개 요약
        summaries = {}
        for agent in ("bear", "fox", "turtle"):
            row = (
                db.query(AgentLog)
                .filter(AgentLog.agent == agent)
                .order_by(AgentLog.id.desc())
                .first()
            )
            if row:
                try:
                    d = json.loads(row.data)
                    summaries[agent] = {
                        "id": row.id,
                        "timestamp": d.get("timestamp"),
                        "status": d.get("status", d.get("action", "?")),
                        "note": d.get("note", "")[:80],
                    }
                except Exception:
                    summaries[agent] = {"id": row.id, "raw": row.data[:80]}
            else:
                summaries[agent] = None
        result["latest_by_agent"] = summaries
        db.close()
    except Exception as e:
        result["db_query_error"] = traceback.format_exc()

    return result
