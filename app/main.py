from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.ai_logs_router import router as ai_logs_router
from app.routes.portfolio_router import router as portfolio_router
from app.routes.fox_logs_router import router as fox_logs_router
from app.routes.visitor_router import router as visitor_router
from app.routes.profit_history_router import router as profit_history_router
import os, json
from pathlib import Path
import firebase_admin
from firebase_admin import credentials

FIREBASE_JSON_ENV = os.getenv("FIREBASE_CREDENTIALS_JSON")
FIREBASE_FILE_PATH = Path(__file__).resolve().parent.parent / "firebase-service-account.json"

if FIREBASE_JSON_ENV and not FIREBASE_FILE_PATH.exists():
    FIREBASE_FILE_PATH.write_text(FIREBASE_JSON_ENV, encoding="utf-8")

if not firebase_admin._apps:
    cred = credentials.Certificate(str(FIREBASE_FILE_PATH))
    firebase_admin.initialize_app(cred)

def _init_accounts():
    """서버 시작 시 에이전트별 초기 계좌가 없으면 자동 생성"""
    from app.db.database import SessionLocal
    from app.db.models import Account

    AGENTS = ["fox", "turtle", "bear"]
    INITIAL_CASH = 10_000.0  # ✅ $10,000

    db = SessionLocal()
    try:
        for agent in AGENTS:
            exists = db.query(Account).filter(Account.agent == agent).first()
            if not exists:
                db.add(Account(agent=agent, cash=INITIAL_CASH))
                print(f"[계좌 초기화] {agent} → ${INITIAL_CASH:,.0f}")
            else:
                print(f"[계좌 확인] {agent} → 현재 잔액 ${exists.cash:,.0f}")
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _init_accounts()
    yield


api = FastAPI(lifespan=lifespan)

api.include_router(ai_logs_router)
api.include_router(portfolio_router)
api.include_router(fox_logs_router)
api.include_router(visitor_router)
api.include_router(profit_history_router)

origins = [
    "http://localhost:5173",
    "https://hj-two-pied.vercel.app",
]

api.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
