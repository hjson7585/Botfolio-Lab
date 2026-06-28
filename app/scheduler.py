from apscheduler.schedulers.background import BackgroundScheduler

from app.services.industry_bear_agent import run_industry_bear

scheduler = BackgroundScheduler()

# 테스트용:
# 1분마다 실행
scheduler.add_job(run_industry_bear, "interval", minutes=30)

scheduler.start()
