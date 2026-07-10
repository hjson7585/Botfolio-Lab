# app/routes/visitor_router.py
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import func, cast, Date
from app.db.database import SessionLocal
from app.db.models import Visitor

router = APIRouter()


class VisitRequest(BaseModel):
    session_id: str  # 프론트에서 생성한 UUID v4 (기존 호환 유지)


def _get_client_ip(request: Request) -> str:
    """
    Reverse proxy(Railway 등) 환경을 고려해
    X-Forwarded-For 헤더 → 실제 클라이언트 IP 순으로 추출.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # "1.2.3.4, 5.6.7.8" 형태일 때 맨 앞(실제 클라이언트) IP 사용
        return forwarded.split(",")[0].strip()
    return request.client.host


@router.post("/visit")
def record_visit(body: VisitRequest, request: Request):
    """
    IP당 24시간 이내 1회만 카운트.
    같은 IP에서 24시간 이내 재방문 시 중복 기입 안 함.
    (기존 session_id 파라미터는 프론트 호환을 위해 그대로 수신하되 집계에 사용하지 않음)
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        since_24h = now - timedelta(hours=24)

        # ── IP 기준 24시간 이내 방문 여부 체크 ──────────────────
        already = (
            db.query(Visitor)
            .filter(
                Visitor.session_id == _get_client_ip(request),  # IP를 식별자로 사용
                Visitor.visited_at >= since_24h,
            )
            .first()
        )
        if already:
            return {"recorded": False, "reason": "duplicate"}

        # IP를 session_id 컬럼에 저장 (스키마 변경 없이 재활용)
        db.add(Visitor(session_id=_get_client_ip(request), visited_at=now))
        db.commit()
        return {"recorded": True}
    finally:
        db.close()


@router.get("/visit-count")
def get_visit_count():
    """전체 방문자 수 (IP 기준 중복 제거)"""
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
