from apscheduler.schedulers.background import BackgroundScheduler
from zoneinfo import ZoneInfo

from app.services.industry_bear_agent import run_industry_bear

NY_TZ = ZoneInfo("America/New_York")

scheduler = BackgroundScheduler(timezone=NY_TZ)

scheduler.add_job(
    run_industry_bear,
    trigger="cron",
    hour=10,
    minute=31,
    second=0,
    day_of_week="mon-fri",
    timezone=NY_TZ,
    id="industry_bear_daily_job",
    replace_existing=True,
    max_instances=1,
    coalesce=True,
    misfire_grace_time=3600,
)

scheduler.start()
