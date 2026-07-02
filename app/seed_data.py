from app.db.database import SessionLocal
from app.db.models import Account

db = SessionLocal()

AGENTS = ["fox", "turtle", "bear"]
INITIAL_CASH = 10000.0

for agent in AGENTS:
    existing = db.query(Account).filter(Account.agent == agent).first()
    if not existing:
        db.add(Account(agent=agent, cash=INITIAL_CASH))
        print(f"[{agent}] 초기 자금 ${INITIAL_CASH:,.0f} 생성 완료")
    else:
        print(f"[{agent}] 이미 존재 — 스킵 (현재 잔액: ${existing.cash:,.0f})")

db.commit()
db.close()

print("초기 자금 세팅 완료")
