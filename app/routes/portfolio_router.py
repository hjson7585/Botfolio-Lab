from fastapi import APIRouter
import yfinance as yf
from app.db.database import SessionLocal
from app.db.models import Portfolio, Account

router = APIRouter()


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

        # 프리마켓
        if market_state == "PRE":
            price = info.get("preMarketPrice")
            if price and price > 0:
                return round(float(price), 2)

        # 애프터마켓
        if market_state in ("POST", "POSTPOST"):
            price = info.get("postMarketPrice")
            if price and price > 0:
                return round(float(price), 2)

        # 정규장
        price = info.get("regularMarketPrice")
        if price and price > 0:
            return round(float(price), 2)

        # 최후 fallback: 1분봉 prepost 포함
        hist = ticker.history(period="1d", interval="1m", prepost=True)
        if not hist.empty:
            return round(float(hist.iloc[-1]["Close"]), 2)

    except Exception as e:
        print(f"[가격 조회 오류] {symbol}: {e}")

    return round(fallback, 2)


@router.get("/portfolio")
def get_portfolio():
    db = SessionLocal()
    try:
        items = db.query(Portfolio).all()
        account = db.query(Account).first()
        cash = account.cash if account else 0

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
