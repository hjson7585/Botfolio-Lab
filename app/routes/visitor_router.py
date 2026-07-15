from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from pydantic import BaseModel
from firebase_admin import firestore

router = APIRouter()

VISITOR_COLLECTION = "visitors"


def _get_db():
    return firestore.client()


class VisitRequest(BaseModel):
    session_id: str


def _to_kst(dt):
    if dt is None:
        return None

    if hasattr(dt, "to_datetime"):
        dt = dt.to_datetime()

    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except Exception:
            return None

    if not isinstance(dt, datetime):
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    kst = timezone(timedelta(hours=9))
    return dt.astimezone(kst)


def _pick_visit_datetime(data: dict):
    candidates = [
        data.get("visitedAt"),
        data.get("visited_at"),
        data.get("createdAt"),
        data.get("created_at"),
        data.get("lastVisitedAt"),
        data.get("last_visited_at"),
    ]

    for value in candidates:
        dt = _to_kst(value)
        if dt:
            return dt
    return None


@router.post("/visit")
def track_visit(body: VisitRequest):
    now = datetime.now(timezone.utc)
    db = _get_db()
    ref = db.collection(VISITOR_COLLECTION).document(body.session_id)
    snap = ref.get()

    if snap.exists:
        ref.set(
            {
                "lastVisitedAt": now,
            },
            merge=True,
        )
    else:
        ref.set(
            {
                "session_id": body.session_id,
                "visitedAt": now,
                "lastVisitedAt": now,
            }
        )

    return {"ok": True}


@router.get("/visit-count")
def visit_count():
    db = _get_db()
    docs = db.collection(VISITOR_COLLECTION).stream()
    total = sum(1 for _ in docs)
    return {"total": total}


@router.get("/visit-today")
def visit_today():
    db = _get_db()
    docs = db.collection(VISITOR_COLLECTION).stream()

    kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(kst)
    today_str = now_kst.strftime("%Y-%m-%d")

    count = 0
    for doc in docs:
        data = doc.to_dict() or {}
        dt = _pick_visit_datetime(data)
        if dt and dt.strftime("%Y-%m-%d") == today_str:
            count += 1

    return {"today": count}


@router.get("/visit-daily")
def visit_daily(days: int = 30):
    db = _get_db()
    docs = db.collection(VISITOR_COLLECTION).stream()

    kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(kst)
    start_date = (now_kst - timedelta(days=days - 1)).date()

    counter = Counter()

    for doc in docs:
        data = doc.to_dict() or {}
        dt = _pick_visit_datetime(data)
        if not dt:
            continue

        d = dt.date()
        if d >= start_date:
            counter[d.strftime("%m/%d")] += 1

    result = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        key = d.strftime("%m/%d")
        result.append({"date": key, "count": counter.get(key, 0)})

    return result
