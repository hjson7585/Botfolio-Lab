# DB 세션을 생성하는 도구 import
from app.db.database import SessionLocal

# Account 테이블(모델) 클래스 import
from app.db.models import Account

# 실제 DB 작업에 사용할 세션 객체 생성
db = SessionLocal()

# Account 객체 생성
# cash=100000 은 초기 보유 현금을 100000으로 설정한다는 뜻
account = Account(cash=100000)

# 위에서 만든 account 객체를 DB 세션에 추가
# 아직 실제 DB에 저장된 것은 아니고, 저장할 준비 상태
db.add(account)

# 세션에 추가한 변경사항을 실제 DB에 저장(커밋)
db.commit()

# 사용이 끝난 세션 닫기
db.close()

# 콘솔에 작업 완료 메시지 출력
print("초기 자금 생성 완료")
