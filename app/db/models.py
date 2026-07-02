from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime
from app.db.database import Base


class Portfolio(Base):
    __tablename__ = "portfolio"
    id = Column(Integer, primary_key=True, index=True)
    agent = Column(String, index=True, default="bear")  # ✅ 추가: fox / turtle / bear
    symbol = Column(String, index=True)
    quantity = Column(Integer)
    average_price = Column(Float)


class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True, index=True)
    agent = Column(String, index=True, default="bear")  # ✅ 추가
    symbol = Column(String)
    action = Column(String)
    quantity = Column(Integer)
    price = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)  # ✅ 추가


class Account(Base):
    __tablename__ = "account"
    id = Column(Integer, primary_key=True, index=True)
    agent = Column(
        String, unique=True, index=True, default="bear"
    )  # ✅ 추가: 에이전트별 계좌
    cash = Column(Float)


# ── 방문자 테이블 ──────────────────────────────────────────
class Visitor(Base):
    __tablename__ = "visitors"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    visited_at = Column(DateTime, index=True)
