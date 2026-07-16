# app/db/models.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from app.db.database import Base


class Portfolio(Base):
    __tablename__ = "portfolio"
    id = Column(Integer, primary_key=True, index=True)
    agent = Column(String, index=True, default="bear")
    symbol = Column(String, index=True)
    quantity = Column(Integer)
    average_price = Column(Float)


class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True, index=True)
    agent = Column(String, index=True, default="bear")
    symbol = Column(String)
    action = Column(String)
    quantity = Column(Integer)
    price = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


class Account(Base):
    __tablename__ = "account"
    id = Column(Integer, primary_key=True, index=True)
    agent = Column(String, unique=True, index=True, default="bear")
    cash = Column(Float)


# ── 에이전트 실행 로그 (파일 대신 DB 저장) ─────────────
class AgentLog(Base):
    __tablename__ = "agent_logs"
    id = Column(Integer, primary_key=True, index=True)
    agent = Column(String, index=True)  # bear / fox / turtle
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    data = Column(Text)  # JSON 문자열로 저장


class Visitor(Base):
    __tablename__ = "visitors"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    ip_address = Column(String, index=True, nullable=True)
    visited_at = Column(DateTime, index=True)
