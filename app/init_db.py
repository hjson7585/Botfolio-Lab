# 데이터베이스 연결 정보(엔진)를 가져옴
# engine은 실제 DB와 연결해주는 역할을 함
from app.db.database import engine

# 우리가 정의한 테이블 모델들의 기본 클래스(Base)를 가져옴
from app.db.models import Base

# Base에 등록된 모든 테이블(모델)을 실제 DB에 생성
# 즉, Portfolio 같은 클래스가 있으면 DB에 테이블이 만들어짐
Base.metadata.create_all(bind=engine)

# 작업이 끝났다는 것을 콘솔에 출력
print("DB 생성 완료")
