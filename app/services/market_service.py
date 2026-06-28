import yfinance as yf

MARKET_SYMBOLS = ["SPY", "QQQ", "^VIX", "^TNX"]


def get_market_data():

    result = []

    for symbol in MARKET_SYMBOLS:

        try:

            stock = yf.Ticker(symbol)

            hist = stock.history(period="5d")

            current_price = hist.iloc[-1]["Close"]

            avg_price = hist["Close"].mean()

            change = ((current_price - avg_price) / avg_price) * 100

            result.append(
                {
                    "symbol": symbol,
                    "current_price": round(current_price, 2),
                    "change_percent": round(change, 2),
                }
            )

        except Exception as e:

            print("시장 데이터 수집 실패")

            print(e)

    return result
