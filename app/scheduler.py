# scheduler.py
from zoneinfo import ZoneInfo
from apscheduler.schedulers.background import BackgroundScheduler
from app.services.industry_bear_agent import run_industry_bear
from app.services.momentum_fox_agent import run_momentum_fox

NY_TZ = ZoneInfo("America/New_York")
scheduler = BackgroundScheduler(timezone=NY_TZ)

# 인더스트리곰: 평일 뉴욕 10:31
scheduler.add_job(
    run_industry_bear,
    trigger="cron",
    hour=10,
    minute=31,
    day_of_week="mon-fri",
    timezone=NY_TZ,
    id="industry_bear_daily_job",
    replace_existing=True,
    max_instances=1,
    coalesce=True,
    misfire_grace_time=3600,
)

# 모멘텀여우: 평일 뉴욕 10:35 (4분 뒤)
scheduler.add_job(
    run_momentum_fox,
    trigger="cron",
    hour=10,
    minute=35,
    day_of_week="mon-fri",
    timezone=NY_TZ,
    id="momentum_fox_daily_job",
    replace_existing=True,
    max_instances=1,
    coalesce=True,
    misfire_grace_time=3600,
)

scheduler.start()
