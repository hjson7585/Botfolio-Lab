from fastapi import APIRouter
import yfinance as yf
from app.db.database import SessionLocal
from app.db.models import Portfolio, Account

router = APIRouter()


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
            try:
                hist = yf.Ticker(item.symbol).history(period="1d")
                current_price = (
                    round(float(hist.iloc[-1]["Close"]), 2)
                    if not hist.empty
                    else item.average_price
                )
            except Exception:
                current_price = item.average_price

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
