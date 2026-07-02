import yfinance as yf
from app.db.database import SessionLocal
from app.db.models import Portfolio, Trade, Account


def buy_stock(symbol: str, quantity: int = 0, use_all_cash: bool = False):
    db = SessionLocal()
    try:
        info = yf.Ticker(symbol).info
        market_state = info.get("marketState", "")
        if market_state == "PRE":
            price = info.get("preMarketPrice") or info.get("regularMarketPrice")
        elif market_state in ("POST", "POSTPOST"):
            price = info.get("postMarketPrice") or info.get("regularMarketPrice")
        else:
            price = info.get("regularMarketPrice")
        if not price:
            hist = yf.Ticker(symbol).history(period="1d")
            price = float(hist.iloc[-1]["Close"]) if not hist.empty else None
        if not price:
            return {"error": "가격 조회 실패"}
        price = float(price)

        account = db.query(Account).first()
        if not account:
            return {"error": "계좌 없음"}

        if use_all_cash:
            quantity = int(account.cash // price)
        if quantity <= 0:
            return {"error": "수량 0"}

        total = price * quantity
        if account.cash < total:
            return {"error": f"잔액 부족 (필요 ${total:.0f}, 보유 ${account.cash:.0f})"}

        account.cash -= total
        portfolio = db.query(Portfolio).filter(Portfolio.symbol == symbol).first()
        if portfolio:
            total_qty = portfolio.quantity + quantity
            portfolio.average_price = (
                (portfolio.average_price * portfolio.quantity) + total
            ) / total_qty
            portfolio.quantity = total_qty
        else:
            portfolio = Portfolio(symbol=symbol, quantity=quantity, average_price=price)
            db.add(portfolio)

        db.add(Trade(symbol=symbol, action="BUY", quantity=quantity, price=price))
        db.commit()
        return {
            "message": f"{symbol} {quantity}주 매수 (${price:.2f}, 합계 ${total:.2f})"
        }
    finally:
        db.close()


def sell_stock(symbol: str, quantity: int):
    db = SessionLocal()
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        current_price = info.get("regularMarketPrice")
        if not current_price:
            hist = stock.history(period="1d")
            if hist.empty:
                return {"error": "가격 조회 실패"}
            current_price = float(hist.iloc[-1]["Close"])
        current_price = float(current_price)

        portfolio = db.query(Portfolio).filter(Portfolio.symbol == symbol).first()
        if not portfolio:
            return {"error": "보유 종목 없음"}
        if portfolio.quantity < quantity:
            return {"error": "수량 부족"}

        total_value = current_price * quantity
        account = db.query(Account).first()
        account.cash += total_value
        portfolio.quantity -= quantity

        if portfolio.quantity == 0:
            db.delete(portfolio)

        trade = Trade(
            symbol=symbol, action="SELL", quantity=quantity, price=current_price
        )
        db.add(trade)
        db.commit()

        return {"message": f"{symbol} {quantity}주 매도 완료"}
    finally:
        db.close()
