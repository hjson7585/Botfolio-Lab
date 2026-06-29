import yfinance as yf
from app.db.database import SessionLocal
from app.db.models import Portfolio, Trade, Account


def buy_stock(symbol: str, quantity: int = 0, use_all_cash: bool = False):
    db = SessionLocal()
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        market_state = info.get("marketState", "")

        # 시장 상태에 따른 현재가 우선순위
        if market_state == "PRE":
            current_price = info.get("preMarketPrice") or info.get("regularMarketPrice")
        elif market_state in ("POST", "POSTPOST"):
            current_price = info.get("postMarketPrice") or info.get(
                "regularMarketPrice"
            )
        else:
            current_price = info.get("regularMarketPrice")

        if not current_price:
            hist = stock.history(period="1d")
            if hist.empty:
                return {"error": "가격 조회 실패"}
            current_price = float(hist.iloc[-1]["Close"])

        current_price = float(current_price)

        account = db.query(Account).first()
        if not account:
            return {"error": "계좌 없음"}

        # 전액 매수: 보유 현금으로 최대 수량 계산
        if use_all_cash:
            quantity = int(account.cash // current_price)

        if quantity <= 0:
            return {"error": "매수 가능 수량 없음 (잔액 부족)"}

        total_cost = current_price * quantity

        if account.cash < total_cost:
            return {"error": "잔액 부족"}

        account.cash -= total_cost

        portfolio = db.query(Portfolio).filter(Portfolio.symbol == symbol).first()
        if portfolio:
            total_qty = portfolio.quantity + quantity
            new_avg = (
                (portfolio.average_price * portfolio.quantity) + total_cost
            ) / total_qty
            portfolio.quantity = total_qty
            portfolio.average_price = new_avg
        else:
            portfolio = Portfolio(
                symbol=symbol, quantity=quantity, average_price=current_price
            )
            db.add(portfolio)

        trade = Trade(
            symbol=symbol, action="BUY", quantity=quantity, price=current_price
        )
        db.add(trade)
        db.commit()

        return {
            "message": f"{symbol} {quantity}주 매수 완료 (단가 ${current_price:,.2f}, 총 ${total_cost:,.2f})"
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
