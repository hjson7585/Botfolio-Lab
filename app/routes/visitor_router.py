# app/routes/visitor_router.py
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import func, cast, Date
from app.db.database import SessionLocal
from app.db.models import Visitor

router = APIRouter()


class VisitRequest(BaseModel):
    session_id: str  # 프론트에서 생성한 UUID v4


def _get_client_ip(request: Request) -> str:
    """프록시(Render/Railway) 환경을 고려해 실제 IP 추출"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/visit")
def record_visit(body: VisitRequest, request: Request):
    """
    IP 기준 24시간 이내 1회만 카운트.
    같은 IP가 24시간 이내에 재방문하면 중복 기입 안 함.
    누적 방문자도 IP 기준 24시간 단위로 집계.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(hours=24)
        ip = _get_client_ip(request)

        # ✅ IP 기준 24시간 이내 중복 체크
        already = (
            db.query(Visitor)
            .filter(
                Visitor.ip_address == ip,
                Visitor.visited_at >= window_start,
            )
            .first()
        )
        if already:
            return {"recorded": False, "reason": "duplicate"}

        db.add(
            Visitor(
                session_id=body.session_id,
                ip_address=ip,
                visited_at=now,
            )
        )
        db.commit()
        return {"recorded": True}
    finally:
        db.close()


@router.get("/visit-count")
def get_visit_count():
    """
    누적 방문자 수.
    같은 IP라도 날짜가 다르면 각각 1명으로 집계 (일별 고유 방문).
    → 전체 레코드 수 = 중복 없는 24시간 단위 방문 횟수
    """
    db = SessionLocal()
    try:
        total = db.query(func.count(Visitor.id)).scalar() or 0
        return {"total": total}
    finally:
        db.close()


@router.get("/visit-daily")
def get_visit_daily(days: int = 30):
    """
    최근 N일 일별 방문자 수 (UTC 기준 날짜).
    반환: [{ date: "06/28", count: 12 }, ...]
    IP 기준 중복 제거가 record_visit에서 이미 처리되므로
    여기서는 단순 날짜별 row 수 집계.
    """
    db = SessionLocal()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        day_col = cast(Visitor.visited_at, Date)

        rows = (
            db.query(
                day_col.label("day"),
                func.count(Visitor.id).label("count"),
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


@router.get("/visit-today")
def get_visit_today():
    """
    오늘(UTC 기준) 방문자 수를 별도 엔드포인트로 제공.
    프론트의 날짜 계산 오차를 서버에서 직접 해결.
    """
    db = SessionLocal()
    try:
        today = datetime.now(timezone.utc).date()
        day_col = cast(Visitor.visited_at, Date)
        count = (
            db.query(func.count(Visitor.id)).filter(day_col == today).scalar()
        ) or 0
        return {"today": count}
    finally:
        db.close()
