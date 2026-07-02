from app.db.database import engine, SessionLocal
from app.db.models import Base

# 신규 테이블 생성 (이미 있으면 스킵)
Base.metadata.create_all(bind=engine)
print("DB 테이블 생성/확인 완료")

# ── 기존 DB 마이그레이션: 새 컬럼이 없으면 ALTER TABLE ──────
MIGRATIONS = [
    (
        "portfolio",
        "agent",
        "ALTER TABLE portfolio ADD COLUMN agent TEXT DEFAULT 'bear'",
    ),
    ("trades", "agent", "ALTER TABLE trades ADD COLUMN agent TEXT DEFAULT 'bear'"),
    ("trades", "created_at", "ALTER TABLE trades ADD COLUMN created_at DATETIME"),
    ("account", "agent", "ALTER TABLE account ADD COLUMN agent TEXT DEFAULT 'bear'"),
]

with engine.connect() as conn:
    for table, column, sql in MIGRATIONS:
        try:
            # PRAGMA table_info로 컬럼 존재 여부 확인
            result = conn.execute(
                __import__("sqlalchemy").text(f"PRAGMA table_info({table})")
            )
            existing_cols = [row[1] for row in result.fetchall()]
            if column not in existing_cols:
                conn.execute(__import__("sqlalchemy").text(sql))
                conn.commit()
                print(f"[마이그레이션] {table}.{column} 컬럼 추가 완료")
            else:
                print(f"[마이그레이션] {table}.{column} 이미 존재 — 스킵")
        except Exception as e:
            print(f"[마이그레이션 오류] {table}.{column}: {e}")

print("마이그레이션 완료")
