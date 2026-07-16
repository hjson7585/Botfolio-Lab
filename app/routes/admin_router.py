# app/routes/admin_router.py
import asyncio
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/admin", tags=["admin"])

LOG_FILES = {
    "bear": Path("logs/ai_logs.json"),
    "fox": Path("logs/fox_logs.json"),
    "turtle": Path("logs/turtle_logs.json"),
}


# ── 기존 에이전트 실행 (자동 스케줄용, 리밸런싱 주기 유지) ──
@router.post("/run/{agent}")
async def run_agent(agent: str):
    if agent == "bear":
        from app.services.industry_bear_agent import run_industry_bear

        await asyncio.to_thread(run_industry_bear)
    elif agent == "fox":
        from app.services.momentum_fox_agent import run_momentum_fox

        await asyncio.to_thread(run_momentum_fox)
    elif agent == "turtle":
        raise HTTPException(status_code=501, detail="배당거북은 아직 미구현입니다.")
    else:
        raise HTTPException(status_code=404, detail=f"알 수 없는 에이전트: {agent}")
    return {"ok": True, "message": f"{agent} 에이전트 실행 완료"}


# ── 🐻 손절/익절 전용 실행 ──────────────────────────────
@router.post("/run/bear/stopcheck")
async def run_bear_stopcheck():
    from app.services.industry_bear_agent import run_industry_bear_stopcheck

    result = await asyncio.to_thread(run_industry_bear_stopcheck)
    return {"ok": True, "message": "손절/익절 체크 완료", "result": result}


# ── 🐻 리밸런싱 강제 실행 ───────────────────────────────
@router.post("/run/bear/rebalance")
async def run_bear_rebalance():
    from app.services.industry_bear_agent import run_industry_bear_rebalance

    result = await asyncio.to_thread(run_industry_bear_rebalance)
    return {"ok": True, "message": "리밸런싱 강제 실행 완료", "result": result}


# ── 로그 삭제 ───────────────────────────────────────────
@router.delete("/logs/{agent}")
def clear_logs(agent: str):
    if agent not in LOG_FILES:
        raise HTTPException(status_code=404, detail=f"알 수 없는 에이전트: {agent}")
    path = LOG_FILES[agent]
    if path.exists():
        path.write_text("[]", encoding="utf-8")
    return {"ok": True, "message": f"{agent} 로그 초기화 완료"}
