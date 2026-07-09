from datetime import datetime, timezone, timedelta
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, cast, Date
from app.db.database import SessionLocal
from app.db.models import Visitor

router = APIRouter()


class VisitRequest(BaseModel):
    session_id: str  # 프론트에서 생성한 UUID v4


@router.post("/visit")
def record_visit(body: VisitRequest):
    """
    세션당 하루 1번만 카운트.
    같은 session_id + 같은 날짜면 중복 기입 안 함
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        today = now.date()

        already = (
            db.query(Visitor)
            .filter(
                Visitor.session_id == body.session_id,
                cast(Visitor.visited_at, Date) == today,
            )
            .first()
        )
        if already:
            return {"recorded": False, "reason": "duplicate"}

        db.add(Visitor(session_id=body.session_id, visited_at=now))
        db.commit()
        return {"recorded": True}
    finally:
        db.close()


@router.get("/visit-count")
def get_visit_count():
    """전체 방문자 수 (세션 기준 중복 제거)"""
    db = SessionLocal()
    try:
        total = db.query(func.count(func.distinct(Visitor.session_id))).scalar() or 0
        return {"total": total}
    finally:
        db.close()


@router.get("/visit-daily")
def get_visit_daily(days: int = 30):
    """
    최근 N일 일별 방문자 수
    반환: [{ date: "06/28", count: 12 }, ...]
    """
    db = SessionLocal()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        day_col = cast(Visitor.visited_at, Date)

        rows = (
            db.query(
                day_col.label("day"),
                func.count(func.distinct(Visitor.session_id)).label("count"),
            )
            .filter(Visitor.visited_at >= since)
            .group_by(day_col)
            .order_by(day_col)
            .all()
        )

        return [
            {
                "date": str(row.day)[5:].replace("-", "/"),  # "06/28"
                "count": row.count,
            }
            for row in rows
        ]
    except Exception as e:
        print(f"[visit-daily 오류] {e}")
        return []
    finally:
        db.close()
