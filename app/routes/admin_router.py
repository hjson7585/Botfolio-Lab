# app/routes/admin_router.py
import asyncio
import traceback
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/run/bear/rebalance")
async def run_bear_rebalance():
    try:
        from app.services.industry_bear_agent import run_industry_bear_rebalance

        result = await asyncio.to_thread(run_industry_bear_rebalance, False)
        return {"ok": True, "message": "리밸런싱 실행 완료", "result": result}
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[admin 오류] run_bear_rebalance:\n{tb}")
        return JSONResponse(
            status_code=200, content={"ok": False, "error": str(e), "traceback": tb}
        )


@router.post("/run/bear/rebalance/force")
async def run_bear_rebalance_force():
    try:
        from app.services.industry_bear_agent import run_industry_bear_rebalance

        result = await asyncio.to_thread(run_industry_bear_rebalance, True)
        return {"ok": True, "message": "리밸런싱 강제 실행 완료", "result": result}
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[admin 오류] run_bear_rebalance_force:\n{tb}")
        return JSONResponse(
            status_code=200, content={"ok": False, "error": str(e), "traceback": tb}
        )


@router.post("/run/{agent}")
async def run_agent(agent: str):
    if agent == "turtle":
        raise HTTPException(status_code=501, detail="배당거북은 아직 미구현입니다.")
    if agent not in ("bear", "fox"):
        raise HTTPException(status_code=404, detail=f"알 수 없는 에이전트: {agent}")
    try:
        if agent == "bear":
            from app.services.industry_bear_agent import run_industry_bear

            result = await asyncio.to_thread(run_industry_bear)
        elif agent == "fox":
            from app.services.momentum_fox_agent import run_momentum_fox

            result = await asyncio.to_thread(run_momentum_fox)
        return {"ok": True, "message": f"{agent} 에이전트 실행 완료", "result": result}
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[admin 오류] run_agent({agent}):\n{tb}")
        return JSONResponse(
            status_code=200, content={"ok": False, "error": str(e), "traceback": tb}
        )


@router.delete("/logs/{agent}")
def clear_logs(agent: str):
    from app.db.database import SessionLocal
    from app.db.models import AgentLog

    db = SessionLocal()
    try:
        db.query(AgentLog).filter(AgentLog.agent == agent).delete()
        db.commit()
        return {"ok": True, "message": f"{agent} 로그 초기화 완료"}
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=200, content={"ok": False, "error": str(e)})
    finally:
        db.close()
