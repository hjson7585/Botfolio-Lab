# app/routes/profit_history_router.py
import json
from pathlib import Path
from datetime import datetime, date
from fastapi import APIRouter
from app.db.database import SessionLocal
from app.db.models import Portfolio, Account
import yfinance as yf

router = APIRouter()

HISTORY_DIR = Path("logs")
HISTORY_DIR.mkdir(exist_ok=True)


# ── /bear-portfolio ────────────────────────────────────────
# IndustryBearPage가 호출하는 엔드포인트
# 기존 /portfolio 와 동일한 로직, agent='bear' 계좌 사용
@router.get("/bear-portfolio")
def get_bear_portfolio():
    from app.routes.portfolio_router import get_realtime_price

    db = SessionLocal()
    try:
        account = (
            db.query(Account).filter(Account.agent == "bear").first()
            or db.query(Account).first()
        )
        cash = account.cash if account else 0

        # bear 에이전트 포트폴리오 (TURTLE/FOX ETF 제외)
        TURTLE_ETFS = {
            "SCHD",
            "DGRO",
            "VYM",
            "VIG",
            "HDV",
            "SPYD",
            "JEPI",
            "JEPQ",
            "DIVO",
            "VNQ",
            "XLU",
            "NOBL",
        }
        FOX_ETFS = {
            "QQQ",
            "VGT",
            "SOXX",
            "SMH",
            "SPY",
            "VOO",
            "IWM",
            "MTUM",
            "QUAL",
            "TLT",
            "IEF",
            "GLD",
        }

        all_items = db.query(Portfolio).all()
        # agent 컬럼이 있으면 bear만, 없으면 TURTLE/FOX가 아닌 종목
        items = [i for i in all_items if getattr(i, "agent", None) == "bear"]
        if not items:
            items = [
                i
                for i in all_items
                if i.symbol not in TURTLE_ETFS and i.symbol not in FOX_ETFS
            ]

        portfolio_list = []
        total_market_value = 0

        for item in items:
            current_price = get_realtime_price(item.symbol, item.average_price)
            market_value = round(current_price * item.quantity, 2)
            profit_rate = (
                round(
                    ((current_price - item.average_price) / item.average_price) * 100, 2
                )
                if item.average_price
                else 0
            )
            total_market_value += market_value
            portfolio_list.append(
                {
                    "symbol": item.symbol,
                    "quantity": item.quantity,
                    "avg_price": round(item.average_price, 2),
                    "current_price": current_price,
                    "market_value": market_value,
                    "profit_rate": profit_rate,
                    "weight": 0,
                }
            )

        total_asset = round(total_market_value + cash, 2)

        for p in portfolio_list:
            p["weight"] = (
                round((p["market_value"] / total_asset) * 100, 2) if total_asset else 0
            )

        total_cost = sum(p["avg_price"] * p["quantity"] for p in portfolio_list)
        profit_rate_total = (
            round(((total_market_value - total_cost) / total_cost) * 100, 2)
            if total_cost
            else 0
        )

        return {
            "portfolio": portfolio_list,
            "cash": round(cash, 2),
            "total_asset": total_asset,
            "total_market_value": round(total_market_value, 2),
            "profit_rate": profit_rate_total,
        }
    finally:
        db.close()


# ── /profit-history/{agent} ────────────────────────────────
# ProfitChart.jsx가 호출하는 엔드포인트
# logs/profit_history_{agent}.json 에서 읽고,
# 없으면 현재 포트폴리오 수익률로 단일 포인트 반환
@router.get("/profit-history/{agent}")
def get_profit_history(agent: str):
    HISTORY_FILE = HISTORY_DIR / f"profit_history_{agent}.json"

    # 파일이 있으면 읽어서 반환
    if HISTORY_FILE.exists():
        try:
            raw = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            # daily/weekly/monthly/yearly 키가 이미 있으면 그대로 반환
            if isinstance(raw, dict) and "daily" in raw:
                return raw
        except Exception:
            pass

    # 파일 없으면 현재 수익률로 빈 히스토리 구성
    today = date.today().isoformat()
    empty_point = {"date": today, "profit_rate": 0.0, "total_asset": 100000.0}

    return {
        "daily": [empty_point],
        "weekly": [empty_point],
        "monthly": [empty_point],
        "yearly": [empty_point],
    }
