# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.firebase_init import init_firebase
from app.scheduler import start_scheduler, stop_scheduler

init_firebase()


def _init_accounts():
    from app.db.database import SessionLocal
    from app.db.models import Account

    AGENTS = ["fox", "turtle", "bear"]
    INITIAL_CASH = 10_000.0
    db = SessionLocal()
    try:
        for agent in AGENTS:
            rows = db.query(Account).filter(Account.agent == agent).all()
            if len(rows) == 0:
                # ✅ 계좌가 없을 때만 생성 (재배포 시 리셋 방지)
                db.add(Account(agent=agent, cash=INITIAL_CASH))
                print(f"[계좌 초기화] {agent} → ${INITIAL_CASH:,.0f}")
            elif len(rows) > 1:
                # 중복 계좌는 첫 번째만 남기고 삭제
                for r in rows[1:]:
                    db.delete(r)
                print(f"[계좌 중복 정리] {agent} 중복 {len(rows)-1}건 삭제")
            else:
                print(f"[계좌 확인] {agent} ${rows[0].cash:,.0f} 유지")
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db.database import engine
    from app.db.models import Base

    Base.metadata.create_all(bind=engine)
    print("[DB] 테이블 생성/확인 완료")
    _init_accounts()
    start_scheduler()
    yield
    stop_scheduler()


api = FastAPI(lifespan=lifespan)

api.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://hj-two-pied.vercel.app",
        "https://botfolio-lab-frontend.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routes.ai_logs_router import router as ai_logs_router
from app.routes.portfolio_router import router as portfolio_router
from app.routes.fox_logs_router import router as fox_logs_router
from app.routes.visitor_router import router as visitor_router
from app.routes.profit_history_router import router as profit_history_router
from app.routes.turtle_logs_router import router as turtle_logs_router
from app.routes.admin_router import router as admin_router

api.include_router(ai_logs_router)
api.include_router(portfolio_router)
api.include_router(fox_logs_router)
api.include_router(visitor_router)
api.include_router(profit_history_router)
api.include_router(turtle_logs_router)
api.include_router(admin_router)
