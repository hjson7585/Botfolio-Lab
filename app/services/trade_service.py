# app/services/trade_service.py
import yfinance as yf
from app.db.database import SessionLocal
from app.db.models import Portfolio, Trade, Account


def buy_stock(
    symbol: str, quantity: int = 0, use_all_cash: bool = False, agent: str = "bear"
):
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

        # ✅ agent 필터로 해당 에이전트 계좌만 조회
        account = db.query(Account).filter(Account.agent == agent).first()
        if not account:
            return {"error": f"계좌 없음 (agent={agent})"}

        if use_all_cash:
            quantity = int(account.cash // price)
        if quantity <= 0:
            return {"error": "수량 0"}

        total = price * quantity
        if account.cash < total:
            return {"error": f"잔액 부족 (필요 ${total:.0f}, 보유 ${account.cash:.0f})"}

        account.cash -= total

        # ✅ agent + symbol 필터로 해당 에이전트 포트폴리오만 조회
        portfolio = (
            db.query(Portfolio)
            .filter(Portfolio.agent == agent, Portfolio.symbol == symbol)
            .first()
        )
        if portfolio:
            total_qty = portfolio.quantity + quantity
            portfolio.average_price = (
                (portfolio.average_price * portfolio.quantity) + total
            ) / total_qty
            portfolio.quantity = total_qty
        else:
            portfolio = Portfolio(
                agent=agent, symbol=symbol, quantity=quantity, average_price=price
            )
            db.add(portfolio)

        # ✅ Trade에도 agent 기록
        db.add(
            Trade(
                agent=agent, symbol=symbol, action="BUY", quantity=quantity, price=price
            )
        )
        db.commit()
        return {
            "message": f"{symbol} {quantity}주 매수 (${price:.2f}, 합계 ${total:.2f})"
        }
    except Exception as e:
        db.rollback()
        return {"error": f"매수 처리 오류: {str(e)}"}
    finally:
        db.close()


def sell_stock(symbol: str, quantity: int, agent: str = "bear"):
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

        # ✅ agent + symbol 필터
        portfolio = (
            db.query(Portfolio)
            .filter(Portfolio.agent == agent, Portfolio.symbol == symbol)
            .first()
        )
        if not portfolio:
            return {"error": f"보유 종목 없음 (agent={agent}, symbol={symbol})"}
        if portfolio.quantity < quantity:
            return {"error": f"수량 부족 (보유 {portfolio.quantity}, 요청 {quantity})"}

        total_value = current_price * quantity

        # ✅ agent 필터로 계좌 조회
        account = db.query(Account).filter(Account.agent == agent).first()
        if not account:
            return {"error": f"계좌 없음 (agent={agent})"}

        account.cash += total_value
        portfolio.quantity -= quantity

        if portfolio.quantity == 0:
            db.delete(portfolio)

        db.add(
            Trade(
                agent=agent,
                symbol=symbol,
                action="SELL",
                quantity=quantity,
                price=current_price,
            )
        )
        db.commit()
        return {
            "message": f"{symbol} {quantity}주 매도 완료 (수익금 ${total_value:.2f})"
        }
    except Exception as e:
        db.rollback()
        return {"error": f"매도 처리 오류: {str(e)}"}
    finally:
        db.close()
