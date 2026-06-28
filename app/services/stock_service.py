import yfinance as yf

# yfinance 라이브러리를 불러옵니다.
# 이 라이브러리는 야후 파이낸스(Yahoo Finance)에서 주가 데이터를 가져올 때 사용합니다.
# as yf 는 앞으로 yfinance를 짧게 yf 라는 이름으로 쓰겠다는 의미입니다.


def get_stock_price(symbol: str):
    # get_stock_price 라는 함수를 정의합니다.
    # symbol 매개변수는 주식 티커(symbol)를 문자열로 받습니다. (예: "AAPL", "005930.KS")

    stock = yf.Ticker(symbol)
    # yf.Ticker(symbol)를 사용해 특정 종목(symbol)에 대한 객체를 만듭니다.
    # 이 객체를 통해 해당 종목의 여러 가지 데이터를 가져올 수 있습니다.

    data = stock.history(period="1d")
    # 선택한 종목의 과거 주가 데이터를 가져옵니다.
    # period="1d" 는 "최근 1일치 데이터만 가져와라" 라는 뜻입니다.
    # 결과는 표(데이터프레임) 형태로, 날짜별로 Open, Close, High, Low 등의 정보가 들어 있습니다.

    latest = data.iloc[-1]
    # iloc[-1] 은 데이터에서 "마지막 행"을 의미합니다. (가장 최근 날짜의 데이터)
    # latest 변수에는 가장 최근 거래일의 한 줄(Series)이 들어갑니다.

    return {"symbol": symbol, "close": latest["Close"]}
    # 딕셔너리 형태로 결과를 반환합니다.
    # "symbol": 어떤 종목인지 (입력으로 받은 symbol)
    # "close": 그날의 종가(Close 가격)
    # 이 함수는 결국 {"symbol": "AAPL", "close": 123.45} 이런 형태로 값을 돌려줍니다.
