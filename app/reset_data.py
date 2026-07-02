"""
reset_data.py  —  Botfolio 전체 데이터 초기화 스크립트
──────────────────────────────────────────────────────
실행:
    cd 프로젝트루트
    python -m app.reset_data
──────────────────────────────────────────────────────
"""

import json
import os
from app.db.database import SessionLocal, engine
from app.db import models

AGENTS = ["bear", "fox", "turtle"]
INITIAL_CASH = 1000.0

LOG_FILES = [
    "logs/ai_logs.json",
    "logs/fox_logs.json",
    "logs/turtle_logs.json",
]

MODEL_STATE_PATH = "logs/model_state.json"


# ── 1. DB 초기화 ──────────────────────────────────────────
def reset_db():
    print("\n[DB] 초기화 시작...")
    db = SessionLocal()
    try:
        # 보유 종목 전체 삭제
        n = db.query(models.Portfolio).delete()
        print(f"  portfolio   삭제: {n}건")

        # 거래 내역 전체 삭제
        n = db.query(models.Trade).delete()
        print(f"  trades      삭제: {n}건")

        # 방문자 로그 삭제
        if hasattr(models, "Visitor"):
            n = db.query(models.Visitor).delete()
            print(f"  visitors    삭제: {n}건")

        # ── Account: 기존 전체 삭제 후 에이전트별 $1,000 재생성 ──
        db.query(models.Account).delete()
        for agent in AGENTS:
            db.add(models.Account(agent=agent, cash=INITIAL_CASH))
            print(f"  account[{agent}]  → ${INITIAL_CASH:,.2f}")

        db.commit()
        print("[DB] ✅ 커밋 완료")
    except Exception as e:
        db.rollback()
        print(f"[DB] ❌ 오류 발생, 롤백: {e}")
    finally:
        db.close()


# ── 2. JSON 로그 파일 초기화 ─────────────────────────────
def reset_log_files():
    print("\n[LOG] JSON 로그 초기화...")
    for path in LOG_FILES:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        print(f"  {path}  → [] ✅")


# ── 3. model_state.json 초기화 ───────────────────────────
def reset_model_state():
    print("\n[STATE] model_state.json 초기화...")
    state = {
        agent: {
            "holdings": {},
            "cash": INITIAL_CASH,
            "last_rebalance": None,
        }
        for agent in AGENTS
    }
    with open(MODEL_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"  {MODEL_STATE_PATH}  ✅")


# ── 메인 ─────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 52)
    print("  Botfolio 데이터 전체 초기화")
    print("=" * 52)

    reset_db()
    reset_log_files()
    reset_model_state()

    print()
    print("=" * 52)
    print("  ✅ 완료 — 에이전트별 독립 계좌 $1,000 세팅")
    print(f"     🐻 bear   → ${INITIAL_CASH:,.2f}")
    print(f"     🦊 fox    → ${INITIAL_CASH:,.2f}")
    print(f"     🐢 turtle → ${INITIAL_CASH:,.2f}")
    print("=" * 52)
