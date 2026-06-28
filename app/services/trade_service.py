# Yahoo Finance에서 실시간 주가 데이터를 가져오기 위한 라이브러리
import yfinance as yf

# DB 세션 생성 함수 import
from app.db.database import SessionLocal

# DB 모델 import
from app.db.models import Portfolio, Trade, Account


def buy_stock(symbol: str, quantity: int):
    """
    주식을 매수하는 함수
    - 현재가 조회
    - 계좌 잔액 확인
    - 포트폴리오 반영
    - 거래내역 저장
    """

    # DB 세션 열기
    db = SessionLocal()

    # Yahoo Finance에서 종목 객체 생성
    stock = yf.Ticker(symbol)

    # 최근 1일 데이터에서 종가 가져오기
    current_price = stock.history(period="1d").iloc[-1]["Close"]

    # 계좌 정보 1개 조회
    account = db.query(Account).first()

    # 총 매수 금액 계산
    total_cost = current_price * quantity

    # 잔액이 부족하면 매수 중단
    if account.cash < total_cost:
        db.close()
        return {"error": "잔액 부족"}

    # 계좌 잔액 차감
    account.cash -= total_cost

    # 해당 종목이 포트폴리오에 이미 있는지 확인
    portfolio = db.query(Portfolio).filter(Portfolio.symbol == symbol).first()

    # 이미 보유 중이면 수량과 평균단가 갱신
    if portfolio:

        # 기존 수량 + 새로 매수한 수량
        total_quantity = portfolio.quantity + quantity

        # 가중평균 방식으로 새로운 평균단가 계산
        new_avg = (
            (portfolio.average_price * portfolio.quantity) + total_cost
        ) / total_quantity

        # 수량과 평균단가 업데이트
        portfolio.quantity = total_quantity
        portfolio.average_price = new_avg

    else:
        # 처음 매수하는 종목이면 새 포트폴리오 데이터 생성
        portfolio = Portfolio(
            symbol=symbol, quantity=quantity, average_price=current_price
        )

        db.add(portfolio)

    # 거래내역 생성
    trade = Trade(symbol=symbol, action="BUY", quantity=quantity, price=current_price)

    # 거래내역 DB에 추가
    db.add(trade)

    # 변경사항 저장
    db.commit()

    # 세션 종료
    db.close()

    return {"message": f"{symbol} 매수 완료"}


def sell_stock(symbol: str, quantity: int):
    """
    주식을 매도하는 함수
    - 현재가 조회
    - 보유 종목 확인
    - 수량 확인
    - 계좌 잔액 반영
    - 거래내역 저장
    """

    # DB 세션 열기
    db = SessionLocal()

    # Yahoo Finance에서 종목 객체 생성
    stock = yf.Ticker(symbol)

    # 최근 1일 데이터에서 종가 가져오기
    current_price = stock.history(period="1d").iloc[-1]["Close"]

    # 해당 종목이 포트폴리오에 있는지 조회
    portfolio = db.query(Portfolio).filter(Portfolio.symbol == symbol).first()

    # 보유 종목이 없으면 매도 불가
    if not portfolio:
        db.close()
        return {"error": "보유 종목 없음"}

    # 보유 수량보다 많이 팔려고 하면 매도 불가
    if portfolio.quantity < quantity:
        db.close()
        return {"error": "수량 부족"}

    # 총 매도 금액 계산
    total_value = current_price * quantity

    # 계좌 정보 조회
    account = db.query(Account).first()

    # 현금 증가
    account.cash += total_value

    # 포트폴리오 수량 차감
    portfolio.quantity -= quantity

    # 수량이 0이 되면 포트폴리오에서 제거
    if portfolio.quantity == 0:
        db.delete(portfolio)

    # 거래내역 생성
    trade = Trade(symbol=symbol, action="SELL", quantity=quantity, price=current_price)

    # 거래내역 DB에 추가
    db.add(trade)

    # 변경사항 저장
    db.commit()

    # 세션 종료
    db.close()

    return {"message": f"{symbol} 매도 완료"}
