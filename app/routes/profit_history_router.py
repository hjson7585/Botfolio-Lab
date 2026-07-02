import json
from pathlib import Path
from datetime import date
from fastapi import APIRouter
from app.db.database import SessionLocal
from app.db.models import Account

router = APIRouter()

HISTORY_DIR = Path("logs")
HISTORY_DIR.mkdir(exist_ok=True)


def _get_live_total_asset(agent: str) -> float:
    """에이전트별 실시간 총자산 조회 (fallback용)"""
    # 포트폴리오 router 함수 직접 호출
    try:
        if agent == "fox":
            from app.routes.portfolio_router import get_fox_portfolio

            data = get_fox_portfolio()
        elif agent == "turtle":
            from app.routes.portfolio_router import get_turtle_portfolio

            data = get_turtle_portfolio()
        else:  # bear
            from app.routes.portfolio_router import get_bear_portfolio_internal

            data = get_bear_portfolio_internal()
        return float(data.get("total_asset", 10_000.0))
    except Exception:
        # DB에서 cash만이라도 읽기
        db = SessionLocal()
        try:
            account = db.query(Account).filter(Account.agent == agent).first()
            return float(account.cash) if account else 10_000.0
        finally:
            db.close()


def _get_live_profit_rate(agent: str) -> float:
    """에이전트별 실시간 수익률 조회 (fallback용)"""
    try:
        if agent == "fox":
            from app.routes.portfolio_router import get_fox_portfolio

            data = get_fox_portfolio()
        elif agent == "turtle":
            from app.routes.portfolio_router import get_turtle_portfolio

            data = get_turtle_portfolio()
        else:
            from app.routes.portfolio_router import get_bear_portfolio_internal

            data = get_bear_portfolio_internal()
        return float(data.get("profit_rate", 0.0))
    except Exception:
        return 0.0


# ── /bear-portfolio ────────────────────────────────────────
@router.get("/bear-portfolio")
def get_bear_portfolio():
    from app.routes.portfolio_router import get_bear_portfolio_internal

    return get_bear_portfolio_internal()


# ── /profit-history/{agent} ────────────────────────────────
@router.get("/profit-history/{agent}")
def get_profit_history(agent: str):
    HISTORY_FILE = HISTORY_DIR / f"profit_history_{agent}.json"

    # 파일이 있으면 읽어서 반환
    if HISTORY_FILE.exists():
        try:
            raw = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and "daily" in raw:
                return raw
        except Exception:
            pass

    # ✅ 파일 없으면 실시간 총자산·수익률로 fallback 구성
    today = date.today().isoformat()
    live_asset = _get_live_total_asset(agent)
    live_rate = _get_live_profit_rate(agent)

    point = {"date": today, "profit_rate": live_rate, "total_asset": live_asset}

    return {
        "daily": [point],
        "weekly": [point],
        "monthly": [point],
        "yearly": [point],
    }
