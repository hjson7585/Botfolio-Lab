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
    세션당 하루 1회만 카운트.
    같은 session_id + 같은 날짜면 중복 삽입 안 함.
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
    """누적 방문자 수 (세션 기준 중복 제거)"""
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

        rows = (
            db.query(
                cast(Visitor.visited_at, Date).label("day"),
                func.count(func.distinct(Visitor.session_id)).label("count"),
            )
            .filter(Visitor.visited_at >= since)
            .group_by("day")
            .order_by("day")
            .all()
        )

        return [
            {
                "date": str(row.day)[5:].replace("-", "/"),  # "06/28"
                "count": row.count,
            }
            for row in rows
        ]
    finally:
        db.close()
