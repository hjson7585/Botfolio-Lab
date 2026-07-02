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
    """
    우선순위:
    1. 프리/애프터마켓 가격 (info 딕셔너리)
    2. 정규장 현재가 (regularMarketPrice)
    3. 1분봉 prepost=True 최신 종가
    4. fallback (평균 단가)
    """
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
    """공통 포트폴리오 응답 빌더"""
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
        # ✅ agent='bear' 계좌 우선, 없으면 첫 번째 계좌 (하위 호환)
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

        # agent 컬럼 없는 기존 데이터 제외 (FOX/TURTLE ETF가 아닌 것)
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
        # ✅ fox 전용 계좌
        account = (
            db.query(Account).filter(Account.agent == "fox").first()
            or db.query(Account).first()
        )
        cash = account.cash if account else 0
    finally:
        db.close()

    # fox는 JSON 파일에 포트폴리오 저장 (momentum_fox_agent.py 방식 유지)
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
        # ✅ turtle 전용 계좌
        account = (
            db.query(Account).filter(Account.agent == "turtle").first()
            or db.query(Account).first()
        )
        cash = account.cash if account else 0

        items = db.query(Portfolio).filter(Portfolio.symbol.in_(TURTLE_ETFS)).all()

        return _build_portfolio_response(items, cash)
    finally:
        db.close()


@router.get("/turtle-dividend")
def get_turtle_dividend():
    """
    배당거북 누적 배당금 계산
    ─ 계산 방식:
      1. Trade 테이블에서 배당거북 ETF의 BUY 이력 조회
         (보유 시작일 = 최초 매수일)
      2. yfinance dividends 이력에서 보유 기간 중 실제 지급된 배당금 합산
         누적배당금 += 배당지급일 당시 보유수량 × 주당배당금
      3. 현재 보유 중인 종목은 Portfolio 테이블 수량 사용
      4. 반환: 종목별 누적배당금 + 전체 합계
    """
    db = SessionLocal()
    try:
        from datetime import datetime, timezone
        import pandas as pd

        holdings = {
            item.symbol: item.quantity
            for item in db.query(Portfolio)
            .filter(Portfolio.symbol.in_(TURTLE_ETFS))
            .all()
        }

        buy_trades = (
            db.query(Trade)
            .filter(
                Trade.symbol.in_(list(TURTLE_ETFS)),
                Trade.action.in_(["BUY", "buy"]),
            )
            .all()
        )

        first_buy: dict[str, datetime] = {}
        for t in buy_trades:
            sym = t.symbol
            # ✅ created_at 컬럼 정상 참조
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
