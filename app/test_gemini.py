# 운영체제(OS) 관련 기능을 사용하기 위한 모듈
# 여기서는 환경 변수(ENV 변수)를 읽을 때 사용
import os

# .env 파일에 있는 내용을 환경 변수로 불러오는 함수 import
from dotenv import load_dotenv

# 구글 생성형 AI(Gemini) 라이브러리 import
import google.generativeai as genai

# .env 파일을 읽어서 그 안의 값들을 환경 변수로 등록
# 예: .env 안에 GEMINI_API_KEY=xxxxx 가 있으면 환경 변수로 올라감
load_dotenv()


# 환경 변수에서 GEMINI_API_KEY 값 가져오기
# os.getenv("키이름") 으로 환경 변수 값을 읽어올 수 있음
api_key = os.getenv("GEMINI_API_KEY")


# Gemini 라이브러리에 API 키 설정
# 이렇게 해야 이후에 모델을 호출할 수 있음
genai.configure(api_key=api_key)


# 사용할 Gemini 모델 선택
# "gemini-3.5-flash" 라는 이름의 모델을 생성
model = genai.GenerativeModel("gemini-3.5-flash")


# 모델에게 보낼 질문(프롬프트) 작성 및 요청
# generate_content() 에 문자열을 넘기면 해당 내용을 바탕으로 답변 생성
response = model.generate_content("애플 주식 전망을 한줄로 설명해줘")


# 모델이 생성한 텍스트 내용을 콘솔에 출력
print(response.text)
