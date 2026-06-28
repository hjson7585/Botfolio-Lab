# 운영체제(OS) 관련 기능을 사용하는 모듈
# 여기서는 환경 변수(ENV 변수)를 읽어올 때 사용
import os

# .env 파일에 적힌 내용을 환경 변수로 불러오는 함수 import
from dotenv import load_dotenv

# 구글 생성형 AI(Gemini) 를 파이썬에서 사용하기 위한 라이브러리 import
import google.generativeai as genai

# 주식/코인 등의 가격 데이터를 가져올 수 있는 yfinance 라이브러리 import
import yfinance as yf

# 현재 프로젝트 폴더에 있는 .env 파일을 읽어서
# 그 안에 정의된 값들을 환경 변수로 등록
load_dotenv()


# 환경 변수에서 GEMINI_API_KEY 값 읽어오기
# .env 파일에 GEMINI_API_KEY=xxxx 형태로 저장돼 있어야 함
api_key = os.getenv("GEMINI_API_KEY")


# Gemini 라이브러리에 API 키 설정
# 이 설정을 해야 이후에 모델을 호출할 수 있음
genai.configure(api_key=api_key)


# 사용할 Gemini 모델 객체 생성
# "gemini-3.5-flash" 라는 이름의 모델을 선택해서 사용할 준비를 함
model = genai.GenerativeModel("gemini-3.5-flash")


# 특정 종목의 최근 주가 데이터를 가져오는 함수 정의
# symbol: 종목 코드 문자열 (예: "AAPL", "TSLA")
def get_stock_data(symbol: str):

    # yfinance에서 해당 종목의 Ticker 객체 생성
    # 이 객체를 통해 주가 정보, 기업 정보 등을 가져올 수 있음
    stock = yf.Ticker(symbol)

    # 최근 1개월치 주가 이력 데이터를 가져옴
    # 보통 날짜별 Open, High, Low, Close, Volume 등이 포함됨
    history = stock.history(period="1mo")

    # 가져온 데이터 중 "Close"(종가) 컬럼만 선택
    # tail(5) = 마지막 5개 데이터만 가져오기
    # tolist() = 판다스 Series를 일반 Python 리스트로 변환
    closes = history["Close"].tail(5).tolist()

    # 최근 종가 5개를 리스트 형태로 반환
    return closes


# AI에게 매수/매도/홀드 결정을 물어보는 함수
# symbol: 종목 코드 문자열 (예: "AAPL")
def ask_ai_decision(symbol: str):

    # 먼저 해당 종목의 최근 종가 데이터 5개를 가져옴
    closes = get_stock_data(symbol)

    # AI에게 보낼 프롬프트(질문 내용) 문자열을 만들기
    # f""" ... """ 를 사용하면 중간에 {symbol}, {closes} 같은 값을 그대로 넣을 수 있음
    prompt = f"""
    너는 전문 주식 투자 AI다.

    다음은 최근 종가 데이터다.

    종목:
    {symbol}

    최근 종가:
    {closes}

    다음 중 하나만 선택해라:
    BUY
    SELL
    HOLD

    아래 JSON 형식으로만 답변해라.

    {{
        "decision": "BUY",
        "reason": "이유 설명"
    }}
    """

    # 위에서 만든 prompt를 Gemini 모델에 보내서 답변을 생성
    response = model.generate_content(prompt)

    # 모델이 생성한 텍스트(= AI의 결정과 이유)를 그대로 반환
    return response.text
