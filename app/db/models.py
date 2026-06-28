# SQLAlchemy에서 테이블의 컬럼(열)을 정의할 때 사용하는 타입들 import
from sqlalchemy import Column, Integer, String, Float

# 앞에서 만든 Base 클래스 import (모든 테이블 모델이 이걸 상속받음)
from app.db.database import Base


# Portfolio라는 이름의 테이블(모델) 클래스 정의
# Base를 상속받아서 "이 클래스는 DB 테이블이다"라고 알려줌
class Portfolio(Base):

    # 실제 데이터베이스에서 사용할 테이블 이름
    __tablename__ = "portfolio"

    # id 컬럼 정의
    # Integer 타입(정수), primary_key=True는 기본키(유일한 값), index=True는 검색 빠르게 해줌
    id = Column(Integer, primary_key=True, index=True)

    # symbol 컬럼 정의 (예: BTC, ETH 같은 코인/주식 이름)
    # String 타입(문자열), index=True로 검색 속도 향상
    symbol = Column(String, index=True)

    # quantity 컬럼 정의 (보유 수량)
    # Integer 타입(정수)
    quantity = Column(Integer)

    # average_price 컬럼 정의 (평균 매수 가격)
    # Float 타입(소수점 숫자)
    average_price = Column(Float)


# Trade라는 이름의 데이터베이스 테이블(모델) 클래스 정의
# Base를 상속받아서 "이 클래스는 DB 테이블과 연결된다"는 뜻
class Trade(Base):

    # 실제 데이터베이스에 생성될 테이블 이름
    __tablename__ = "trades"

    # id 컬럼 정의
    # Integer = 정수 타입
    # primary_key=True = 기본키(각 행을 구분하는 고유 번호)
    # index=True = 검색 속도를 높이기 위한 인덱스 생성
    id = Column(Integer, primary_key=True, index=True)

    # symbol 컬럼 정의
    # 거래한 종목 코드 저장 (예: AAPL, TSLA)
    # String = 문자열 타입
    symbol = Column(String)

    # action 컬럼 정의
    # 매수/매도 같은 거래 행동 저장
    # 예: "buy", "sell"
    action = Column(String)

    # quantity 컬럼 정의
    # 몇 주(몇 개)를 거래했는지 저장
    # Integer = 정수 타입
    quantity = Column(Integer)

    # price 컬럼 정의
    # 거래 당시 가격 저장
    # Float = 소수점이 있는 숫자 타입
    price = Column(Float)


# Account라는 이름의 데이터베이스 테이블(모델) 클래스 정의
# Base를 상속받아서 이 클래스가 DB 테이블과 연결되도록 함
class Account(Base):

    # 실제 데이터베이스에 생성될 테이블 이름
    __tablename__ = "account"

    # id 컬럼 정의
    # Integer = 정수 타입
    # primary_key=True = 기본키(각 행을 구분하는 고유 번호)
    # index=True = 검색 속도를 높이기 위한 인덱스 생성
    id = Column(Integer, primary_key=True, index=True)

    # cash 컬럼 정의
    # Float = 소수점이 있는 숫자 타입
    # 계좌에 남아 있는 현금 금액을 저장하는 용도
    cash = Column(Float)
