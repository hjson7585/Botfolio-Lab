# SQLAlchemy에서 데이터베이스 연결을 만들 때 사용하는 함수 import
from sqlalchemy import create_engine

# 세션(데이터베이스 작업 단위)과 모델의 기본 클래스 관련 기능 import
from sqlalchemy.orm import sessionmaker, declarative_base

# 사용할 데이터베이스 주소 설정
# sqlite:///./trading.db 는 현재 폴더에 trading.db 파일을 사용한다는 의미
DATABASE_URL = "sqlite:///./trading.db"

# 데이터베이스와 실제로 연결해주는 엔진 생성
engine = create_engine(
    DATABASE_URL,  # 위에서 정의한 DB 경로 사용
    # SQLite를 사용할 때 멀티스레드 오류를 막기 위한 설정
    # 같은 스레드가 아니어도 DB 접근을 허용
    connect_args={"check_same_thread": False},
)

# 데이터베이스 작업을 할 때 사용할 "세션" 생성 도구 설정
SessionLocal = sessionmaker(
    autocommit=False,  # 자동으로 커밋(저장)하지 않음 → 직접 commit() 해야 함
    autoflush=False,  # 자동으로 변경사항을 DB에 반영하지 않음
    bind=engine,  # 위에서 만든 engine(연결 정보)을 사용
)

# ORM 모델(테이블 클래스)을 만들 때 상속받는 기본 클래스 생성
Base = declarative_base()
