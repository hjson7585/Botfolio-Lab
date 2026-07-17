# app/routes/visitor_router.py
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()

KST = timezone(timedelta(hours=9))


class VisitRequest(BaseModel):
    session_id: str


@router.post("/visit")
def track_visit(body: VisitRequest, request: Request):
    """
    방문 기록:
    - 같은 session_id가 오늘(KST) 이미 기록됐으면 스킵 (중복 방지)
    - 오늘 처음 방문이면 새 행 INSERT → 날짜별 누적 보장
    """
    try:
        from app.db.database import SessionLocal
        from app.db.models import Visitor

        db = SessionLocal()
        try:
            now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

            # 오늘(KST) 시작 시각을 UTC naive로 계산
            now_kst = datetime.now(KST)
            today_start_kst = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
            today_start_utc = today_start_kst.astimezone(timezone.utc).replace(
                tzinfo=None
            )

            # 오늘 이미 같은 session_id로 방문 기록이 있으면 스킵
            already_today = (
                db.query(Visitor)
                .filter(
                    Visitor.session_id == body.session_id,
                    Visitor.visited_at >= today_start_utc,
                )
                .first()
            )
            if already_today:
                return {"ok": True, "skipped": True}

            # 오늘 처음 방문 → 새 행 INSERT (기존 행 건드리지 않음)
            ip = request.headers.get(
                "x-forwarded-for",
                request.client.host if request.client else None,
            )
            if ip:
                ip = ip.split(",")[0].strip()

            db.add(
                Visitor(
                    session_id=body.session_id,
                    ip_address=ip,
                    visited_at=now_utc,
                )
            )
            db.commit()
            return {"ok": True, "skipped": False}
        finally:
            db.close()
    except Exception as e:
        return JSONResponse(status_code=200, content={"ok": False, "error": str(e)})


@router.get("/visit-count")
def visit_count():
    """누적 방문자 수 = 전체 행 수 (날짜 무관)"""
    try:
        from app.db.database import SessionLocal
        from app.db.models import Visitor

        db = SessionLocal()
        try:
            total = db.query(Visitor).count()
            return {"total": total}
        finally:
            db.close()
    except Exception as e:
        return JSONResponse(status_code=200, content={"total": 0, "error": str(e)})


@router.get("/visit-today")
def visit_today():
    """오늘(KST) 방문자 수"""
    try:
        from app.db.database import SessionLocal
        from app.db.models import Visitor

        db = SessionLocal()
        try:
            now_kst = datetime.now(KST)
            today_start_kst = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
            today_start_utc = today_start_kst.astimezone(timezone.utc).replace(
                tzinfo=None
            )

            count = (
                db.query(Visitor).filter(Visitor.visited_at >= today_start_utc).count()
            )
            return {"today": count}
        finally:
            db.close()
    except Exception as e:
        return JSONResponse(status_code=200, content={"today": 0, "error": str(e)})


@router.get("/visit-daily")
def visit_daily(days: int = 30):
    """최근 N일 날짜별 방문자 수 (KST 기준, 누적 행 집계)"""
    try:
        from app.db.database import SessionLocal
        from app.db.models import Visitor

        db = SessionLocal()
        try:
            now_kst = datetime.now(KST)
            start_kst = (now_kst - timedelta(days=days - 1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            start_utc = start_kst.astimezone(timezone.utc).replace(tzinfo=None)

            rows = db.query(Visitor).filter(Visitor.visited_at >= start_utc).all()

            counter: Counter = Counter()
            for row in rows:
                if row.visited_at:
                    dt_kst = row.visited_at.replace(tzinfo=timezone.utc).astimezone(KST)
                    counter[dt_kst.strftime("%m/%d")] += 1

            result = []
            for i in range(days):
                d = (start_kst + timedelta(days=i)).strftime("%m/%d")
                result.append({"date": d, "count": counter.get(d, 0)})
            return result
        finally:
            db.close()
    except Exception as e:
        return JSONResponse(status_code=200, content=[])
