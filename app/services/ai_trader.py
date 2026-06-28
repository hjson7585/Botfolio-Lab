# yfinance 라이브러리 import
# 야후 파이낸스에서 주가 데이터를 가져올 때 사용
import yfinance as yf

# trade_service 모듈에서 buy_stock 함수 import
# 매수 처리를 실제로 수행하는 함수
from app.services.trade_service import buy_stock


# AI 자동매매(간단 버전)를 실행하는 함수 정의
def run_ai_trader():

    # 매매 대상이 될 종목 리스트
    symbols = ["AAPL", "TSLA", "MSFT"]

    # 종목 리스트를 하나씩 반복
    for symbol in symbols:

        # 현재 종목의 yfinance Ticker 객체 생성
        stock = yf.Ticker(symbol)

        # 최근 5일치 주가 데이터를 가져옴
        hist = stock.history(period="5d")

        # 가장 최근 종가를 가져옴
        # iloc[-1] = 마지막 행
        # ["Close"] = 종가 컬럼
        current_price = hist.iloc[-1]["Close"]

        # 최근 5일 종가의 평균값 계산
        # 단순 이동평균처럼 사용
        moving_average = hist["Close"].mean()

        # 현재 가격이 최근 평균가보다 높으면 매수 신호로 판단
        if current_price > moving_average:

            # 콘솔에 매수 신호 메시지 출력
            print(f"{symbol} 매수 신호")

            # 해당 종목을 1주 매수
            result = buy_stock(symbol, 1)

            # 매수 결과 출력
            print(result)
