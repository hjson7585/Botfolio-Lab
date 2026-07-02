from sqlalchemy import Column, Integer, String, Float, DateTime
from app.db.database import Base


class Portfolio(Base):
    __tablename__ = "portfolio"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    quantity = Column(Integer)
    average_price = Column(Float)


class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String)
    action = Column(String)
    quantity = Column(Integer)
    price = Column(Float)


class Account(Base):
    __tablename__ = "account"
    id = Column(Integer, primary_key=True, index=True)
    cash = Column(Float)


# ── 방문자 테이블 ──────────────────────────────────────────
class Visitor(Base):
    __tablename__ = "visitors"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)  # 브라우저 세션 UUID (중복 방문 방지)
    visited_at = Column(DateTime, index=True)  # 방문 시각 (UTC)
