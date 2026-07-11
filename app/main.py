from contextlib import asynccontextmanager
from pathlib import Path
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.ai_logs_router import router as ai_logs_router
from app.routes.portfolio_router import router as portfolio_router
from app.routes.fox_logs_router import router as fox_logs_router
from app.routes.visitor_router import router as visitor_router
from app.routes.profit_history_router import router as profit_history_router
from app.firebase_init import init_firebase
from app.routes.turtle_logs_router import router as turtle_logs_router
from app.scheduler import start_scheduler, stop_scheduler

init_firebase()


def _init_accounts():
    """서버 시작 시 에이전트별 계좌를 10,000달러 기준으로 강제 정렬 (중복 행 정리 포함)"""
    from app.db.database import SessionLocal
    from app.db.models import Account

    AGENTS = ["fox", "turtle", "bear"]
    INITIAL_CASH = 10_000.0

    db = SessionLocal()
    try:
        for agent in AGENTS:
            rows = db.query(Account).filter(Account.agent == agent).all()

            if len(rows) == 0:
                db.add(Account(agent=agent, cash=INITIAL_CASH))
                print(f"[계좌 초기화] {agent} → ${INITIAL_CASH:,.0f}")
            elif len(rows) == 1:
                before = float(rows[0].cash or 0)
                rows[0].cash = INITIAL_CASH
                print(f"[계좌 정렬] {agent} ${before:,.0f} → ${INITIAL_CASH:,.0f}")
            else:
                # ✅ 중복 행 정리: 모두 삭제 후 하나만 재생성
                for r in rows:
                    db.delete(r)
                db.flush()
                db.add(Account(agent=agent, cash=INITIAL_CASH))
                print(
                    f"[계좌 중복 정리] {agent} 중복 {len(rows)}건 삭제 → ${INITIAL_CASH:,.0f} 재생성"
                )

        db.commit()
    finally:
        db.close()


def _cleanup_legacy_profit_history():
    """기존 1000달러 기준 수익률 히스토리 파일 자동 삭제"""
    history_dir = Path("logs")
    targets = ["fox", "turtle", "bear"]

    for agent in targets:
        path = history_dir / f"profit_history_{agent}.json"
        if not path.exists():
            print(f"[히스토리 없음] {path.name}")
            continue

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            should_delete = False

            if isinstance(raw, dict):
                for bucket in ["daily", "weekly", "monthly", "yearly"]:
                    rows = raw.get(bucket, [])
                    if not rows:
                        continue

                    for row in rows:
                        asset = row.get("total_asset")
                        if asset is not None and float(asset) <= 1000.0:
                            should_delete = True
                            break
                    if should_delete:
                        break

            if should_delete:
                path.unlink(missing_ok=True)
                print(f"[히스토리 정리] {path.name} 삭제 완료")
            else:
                print(f"[히스토리 유지] {path.name}")
        except Exception as e:
            print(f"[히스토리 정리 스킵] {path.name}: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db.database import engine
    from app.db.models import Base

    Base.metadata.create_all(bind=engine)
    print("[DB] 테이블 생성/확인 완료")
    _init_accounts()
    _cleanup_legacy_profit_history()
    start_scheduler()
    yield
    stop_scheduler()


api = FastAPI(lifespan=lifespan)

api.include_router(ai_logs_router)
api.include_router(portfolio_router)
api.include_router(fox_logs_router)
api.include_router(visitor_router)
api.include_router(profit_history_router)
api.include_router(turtle_logs_router)

origins = [
    "http://localhost:5173",
    "https://hj-two-pied.vercel.app",
    "https://botfolio-lab-frontend.vercel.app",
]

api.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
