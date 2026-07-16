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
    try:
        from app.db.database import SessionLocal
        from app.db.models import Visitor

        db = SessionLocal()
        try:
            now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
            existing = (
                db.query(Visitor).filter(Visitor.session_id == body.session_id).first()
            )
            if existing:
                existing.visited_at = now_utc
            else:
                ip = request.headers.get(
                    "x-forwarded-for", request.client.host if request.client else None
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
            return {"ok": True}
        finally:
            db.close()
    except Exception as e:
        return JSONResponse(status_code=200, content={"ok": False, "error": str(e)})


@router.get("/visit-count")
def visit_count():
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
                    # UTC → KST 변환 후 날짜 집계
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
