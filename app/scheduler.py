# scheduler.py
"""
스케줄러 기준: America/New_York (APScheduler가 DST 자동 처리)
  - 미국 표준시 (EST, UTC-5) 09:31/32/33 → 한국시간 23:31/32/33
  - 미국 서머타임 (EDT, UTC-4) 09:31/32/33 → 한국시간 22:31/32/33

⚠️ 배당거북(dividend_turtle) 에이전트는 아직 구현되지 않아
   해당 job은 임시로 비활성화되어 있습니다.
"""

import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# ── 에이전트 실행 함수 import ──────────────────────────
from app.services.industry_bear_agent import run_industry_bear
from app.services.momentum_fox_agent import run_momentum_fox
# from app.services.dividend_turtle_agent import run_dividend_turtle  # TODO: 미구현

# ── 로거 설정 ──────────────────────────────────────────
logger = logging.getLogger(__name__)

# ── 타임존 ────────────────────────────────────────────
NY_TZ = ZoneInfo("America/New_York")

# ── 스케줄러 초기화 ────────────────────────────────────
scheduler = BackgroundScheduler(timezone=NY_TZ)

# ── 공통 옵션 ──────────────────────────────────────────
_COMMON = dict(
    day_of_week="mon-fri",
    timezone=NY_TZ,
    replace_existing=True,
    max_instances=1,
    coalesce=True,
    misfire_grace_time=3600,
)

# ── 1) 인더스트리곰 — 뉴욕 09:31 (KST 23:31 / DST 22:31) ──
scheduler.add_job(
    run_industry_bear,
    trigger=CronTrigger(
        hour=9,
        minute=31,
        second=0,
        **{k: v for k, v in _COMMON.items() if k in ("day_of_week", "timezone")},
    ),
    id="industry_bear_daily",
    **{k: v for k, v in _COMMON.items() if k not in ("day_of_week", "timezone")},
)

# ── 2) 배당거북 — 미구현으로 임시 비활성화 ──────────────
# scheduler.add_job(
#     run_dividend_turtle,
#     trigger=CronTrigger(
#         hour=9,
#         minute=32,
#         second=0,
#         **{k: v for k, v in _COMMON.items() if k in ("day_of_week", "timezone")},
#     ),
#     id="dividend_turtle_daily",
#     **{k: v for k, v in _COMMON.items() if k not in ("day_of_week", "timezone")},
# )

# ── 3) 모멘텀여우 — 뉴욕 09:33 (KST 23:33 / DST 22:33) ──
scheduler.add_job(
    run_momentum_fox,
    trigger=CronTrigger(
        hour=9,
        minute=33,
        second=0,
        **{k: v for k, v in _COMMON.items() if k in ("day_of_week", "timezone")},
    ),
    id="momentum_fox_daily",
    **{k: v for k, v in _COMMON.items() if k not in ("day_of_week", "timezone")},
)


# ── 스케줄러 시작 / 종료 헬퍼 ──────────────────────────
def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")
        for job in scheduler.get_jobs():
            logger.info("  - [%s] next run: %s", job.id, job.next_run_time)


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
