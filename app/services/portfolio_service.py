# yfinance 라이브러리를 import
# 실제 주식/ETF 등의 현재 가격 데이터를 가져올 때 사용
import yfinance as yf

# DB 작업을 하기 위한 세션 생성 도구 가져오기
from app.db.database import SessionLocal

# 포트폴리오 테이블(모델) 클래스 가져오기
from app.db.models import Portfolio


# 포트폴리오 정보를 가져오는 함수 정의
def get_portfolio():

    # DB와 통신할 세션 생성
    db = SessionLocal()

    # Portfolio 테이블에 있는 모든 레코드(행)를 조회
    # SELECT * FROM portfolio 와 비슷한 역할
    portfolio = db.query(Portfolio).all()

    # 결과를 담을 리스트 초기화 (각 종목별 정보를 dict 형태로 넣을 예정)
    result = []

    # 전체 포트폴리오의 총 평가금액을 저장할 변수 초기화
    total_value = 0

    # DB에서 가져온 각 포트폴리오 종목에 대해 반복
    for item in portfolio:

        # yfinance의 Ticker 객체 생성 (예: "AAPL", "TSLA" 같은 심볼)
        stock = yf.Ticker(item.symbol)

        # 최근 1일치 주가 데이터를 가져오고,
        # iloc[-1]로 마지막 행(가장 최근 데이터)을 선택한 뒤,
        # 그 중 "Close"(종가) 가격만 가져옴
        price = stock.history(period="1d").iloc[-1]["Close"]

        # 현재가(종가) * 보유 수량 = 해당 종목의 현재 평가 금액
        current_value = price * item.quantity

        # 전체 포트폴리오 평가 금액에 이 종목의 평가 금액을 더함
        total_value += current_value

        # 이 종목에 대한 정보를 dict 형태로 result 리스트에 추가
        result.append(
            {
                "symbol": item.symbol,  # 종목 심볼 (예: AAPL)
                "quantity": item.quantity,  # 보유 수량
                "avg_price": item.average_price,  # 평균 매수가
                "current_price": round(price, 2),  # 현재가 (소수 둘째 자리까지 반올림)
                "current_value": round(current_value, 2),  # 현재 평가 금액 (반올림)
            }
        )

    # DB 세션 닫아서 자원 정리
    db.close()

    # 최종 결과를 dict 형태로 반환
    # "stocks"에는 각 종목별 상세 정보 리스트,
    # "total_value"에는 전체 포트폴리오 총 평가 금액
    return {"stocks": result, "total_value": round(total_value, 2)}
