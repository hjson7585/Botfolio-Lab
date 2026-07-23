from fastapi import APIRouter
import yfinance as yf
from app.db.database import SessionLocal
from app.db.models import Portfolio, Account, Trade

router = APIRouter()

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


def get_realtime_price(symbol: str, fallback: float) -> float:
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        market_state = info.get("marketState", "")

        if market_state == "PRE":
            price = info.get("preMarketPrice")
            if price and price > 0:
                return round(float(price), 2)

        if market_state in ("POST", "POSTPOST"):
            price = info.get("postMarketPrice")
            if price and price > 0:
                return round(float(price), 2)

        price = info.get("regularMarketPrice")
        if price and price > 0:
            return round(float(price), 2)

        hist = ticker.history(period="1d", interval="1m", prepost=True)
        if not hist.empty:
            return round(float(hist.iloc[-1]["Close"]), 2)

    except Exception as e:
        print(f"[가격 조회 오류] {symbol}: {e}")

    return round(fallback, 2)


def _build_portfolio_response(items, cash):
    portfolio_list = []
    total_market_value = 0

    for item in items:
        current_price = get_realtime_price(item.symbol, item.average_price)
        market_value = round(current_price * item.quantity, 2)
        profit_rate = (
            round(((current_price - item.average_price) / item.average_price) * 100, 2)
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


@router.get("/portfolio")
def get_portfolio():
    """인더스트리곰 전용 (bear)"""
    db = SessionLocal()
    try:
        account = (
            db.query(Account).filter(Account.agent == "bear").first()
            or db.query(Account).first()
        )
        cash = account.cash if account else 0

        items = (
            db.query(Portfolio)
            .filter((Portfolio.agent == "bear") | (Portfolio.agent == None))
            .all()
        )

        bear_symbols = set(TURTLE_ETFS) | set(FOX_ETFS)
        items = [i for i in items if i.symbol not in bear_symbols] or items

        return _build_portfolio_response(items, cash)
    finally:
        db.close()


@router.get("/fox-portfolio")
def get_fox_portfolio():
    """모멘텀여우 전용 (fox) — JSON 파일 기반 포트폴리오 + DB 계좌"""
    import json
    from pathlib import Path

    PORT_FILE = Path("logs/fox_portfolio.json")

    db = SessionLocal()
    try:
        account = (
            db.query(Account).filter(Account.agent == "fox").first()
            or db.query(Account).first()
        )
        cash = account.cash if account else 0
    finally:
        db.close()

    if PORT_FILE.exists():
        try:
            raw = json.loads(PORT_FILE.read_text(encoding="utf-8"))
        except Exception:
            raw = []
    else:
        raw = []

    portfolio_list = []
    total_market_value = 0

    for pos in raw:
        symbol = pos.get("symbol", "")
        avg_price = float(pos.get("avg_price", 0))
        quantity = int(pos.get("quantity", 1))

        current_price = get_realtime_price(symbol, avg_price)
        market_value = round(current_price * quantity, 2)
        profit_rate = (
            round(((current_price - avg_price) / avg_price) * 100, 2)
            if avg_price
            else 0
        )
        total_market_value += market_value

        portfolio_list.append(
            {
                "symbol": symbol,
                "quantity": quantity,
                "avg_price": round(avg_price, 2),
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


@router.get("/turtle-portfolio")
def get_turtle_portfolio():
    """배당거북 전용 (turtle)"""
    db = SessionLocal()
    try:
        account = (
            db.query(Account).filter(Account.agent == "turtle").first()
            or db.query(Account).first()
        )
        cash = account.cash if account else 0

        # ✅ 핵심 수정: agent='turtle' 필터 추가 — bear가 매수한 SOXX/XLU 혼입 차단
        items = (
            db.query(Portfolio)
            .filter(
                Portfolio.agent == "turtle",
                Portfolio.symbol.in_(TURTLE_ETFS),
            )
            .all()
        )

        return _build_portfolio_response(items, cash)
    finally:
        db.close()


@router.get("/turtle-dividend")
def get_turtle_dividend():
    """
    배당거북 누적 배당금 계산
    """
    db = SessionLocal()
    try:
        from datetime import datetime, timezone
        import pandas as pd

        # ✅ 핵심 수정: agent='turtle' 필터 추가 — bear 포지션 혼입 차단
        holdings = {
            item.symbol: item.quantity
            for item in db.query(Portfolio)
            .filter(
                Portfolio.agent == "turtle",
                Portfolio.symbol.in_(TURTLE_ETFS),
            )
            .all()
        }

        buy_trades = (
            db.query(Trade)
            .filter(
                Trade.agent == "turtle",  # ✅ agent 필터 추가
                Trade.symbol.in_(list(TURTLE_ETFS)),
                Trade.action.in_(["BUY", "buy"]),
            )
            .all()
        )

        first_buy: dict[str, datetime] = {}
        for t in buy_trades:
            sym = t.symbol
            if hasattr(t, "created_at") and t.created_at:
                ts = t.created_at
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if sym not in first_buy or ts < first_buy[sym]:
                    first_buy[sym] = ts
            else:
                if sym not in first_buy:
                    one_year_ago = datetime.now(timezone.utc).replace(
                        year=datetime.now().year - 1
                    )
                    first_buy[sym] = one_year_ago

        dividend_by_symbol = {}
        total_dividend = 0.0

        for symbol, qty in holdings.items():
            try:
                ticker = yf.Ticker(symbol)
                divs = ticker.dividends

                if divs.empty:
                    dividend_by_symbol[symbol] = {
                        "symbol": symbol,
                        "quantity": qty,
                        "total_dividend": 0.0,
                        "dividend_count": 0,
                    }
                    continue

                if divs.index.tzinfo is None:
                    divs.index = divs.index.tz_localize("UTC")

                start_dt = first_buy.get(
                    symbol, pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=365)
                )
                if isinstance(start_dt, datetime):
                    start_dt = pd.Timestamp(start_dt)

                filtered = divs[divs.index >= start_dt]
                sym_dividend = round(float(filtered.sum()) * qty, 2)
                dividend_count = len(filtered)

                dividend_by_symbol[symbol] = {
                    "symbol": symbol,
                    "quantity": qty,
                    "total_dividend": sym_dividend,
                    "dividend_count": dividend_count,
                    "per_share_total": round(float(filtered.sum()), 4),
                }
                total_dividend += sym_dividend

            except Exception as e:
                print(f"[배당 조회 오류] {symbol}: {e}")
                dividend_by_symbol[symbol] = {
                    "symbol": symbol,
                    "quantity": qty,
                    "total_dividend": 0.0,
                    "dividend_count": 0,
                }

        return {
            "total_dividend": round(total_dividend, 2),
            "dividend_by_symbol": list(dividend_by_symbol.values()),
        }

    finally:
        db.close()


def get_bear_portfolio_internal():
    """bear 포트폴리오 내부 호출용"""
    db = SessionLocal()
    try:
        account = (
            db.query(Account).filter(Account.agent == "bear").first()
            or db.query(Account).first()
        )
        cash = account.cash if account else 0

        bear_exclude = set(TURTLE_ETFS) | set(FOX_ETFS)
        all_items = db.query(Portfolio).all()
        items = [i for i in all_items if getattr(i, "agent", None) == "bear"]
        if not items:
            items = [i for i in all_items if i.symbol not in bear_exclude]

        return _build_portfolio_response(items, cash)
    finally:
        db.close()
