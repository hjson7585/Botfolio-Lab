# app/db/database.py
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ── DB 주소 결정 ───────────────────────────────────────
# Railway 환경변수 DATABASE_URL이 있으면 PostgreSQL 사용
# 없으면 (로컬 개발 환경) 기존 SQLite 사용
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./trading.db")

# Railway PostgreSQL URL은 "postgres://" 형식으로 제공되는데
# SQLAlchemy는 "postgresql://" 형식만 인식하므로 자동 변환
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ── 엔진 생성 ──────────────────────────────────────────
# SQLite와 PostgreSQL은 설정 옵션이 다르므로 분기 처리
if DATABASE_URL.startswith("sqlite"):
    # SQLite: 멀티스레드 허용 옵션 필요
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    # PostgreSQL: 별도 옵션 불필요
    engine = create_engine(DATABASE_URL)

# ── 세션 설정 (기존과 동일) ────────────────────────────
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()
