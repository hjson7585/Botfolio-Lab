# ai_service 모듈에서 ask_ai_decision 함수만 가져오기
# 이 함수는 종목 코드를 넣으면 AI에게 매수/매도/홀드 결정을 물어보는 역할을 함
from app.services.ai_service import ask_ai_decision

# "AAPL" 종목에 대해 AI에게 의사결정을 요청
# 결과는 보통 JSON 형식의 문자열(또는 그와 비슷한 텍스트)로 반환될 것
result = ask_ai_decision("AAPL")

# AI가 내려준 결정/이유를 콘솔에 출력
print(result)
