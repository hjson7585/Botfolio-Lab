# app/routes/ai_logs_router.py
import json
from fastapi import APIRouter
from app.db.database import SessionLocal, DATABASE_URL
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


# ✅ 진단 엔드포인트 — DB 연결 상태 및 로그 개수 직접 확인
@router.get("/ai-logs/debug")
def debug_ai_logs():
    import traceback
    from app.db.database import engine
    from app.db.models import Base

    result = {
        "database_url_type": "postgresql" if "postgresql" in DATABASE_URL else "sqlite",
        "database_url_masked": (
            DATABASE_URL[:30] + "..." if len(DATABASE_URL) > 30 else DATABASE_URL
        ),
    }

    # 테이블 강제 생성 시도
    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
        result["table_create"] = "ok"
    except Exception as e:
        result["table_create"] = f"ERROR: {e}"

    # 전체 AgentLog 개수 조회
    try:
        db = SessionLocal()
        total = db.query(AgentLog).count()
        bear_total = db.query(AgentLog).filter(AgentLog.agent == "bear").count()
        db.close()
        result["total_logs"] = total
        result["bear_logs"] = bear_total
    except Exception as e:
        result["db_query_error"] = traceback.format_exc()

    # 테스트 로그 직접 INSERT
    try:
        db = SessionLocal()
        test_entry = AgentLog(
            agent="bear",
            data=json.dumps(
                {
                    "agent": "인더스트리곰",
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
