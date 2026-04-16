from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "sochron1k",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Bangkok",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=300,
    task_time_limit=600,
)

celery_app.conf.beat_schedule = {
    # Forex Factory — ทุก 3 นาที (economic calendar)
    "scrape-forex-factory": {
        "task": "app.tasks.news_tasks.scrape_source",
        "schedule": 180.0,
        "args": ["forex_factory"],
        "options": {"queue": "scraping"},
    },
    # Investing.com — ทุก 1 ชม.
    "scrape-investing": {
        "task": "app.tasks.news_tasks.scrape_source",
        "schedule": crontab(minute=5),
        "args": ["investing"],
        "options": {"queue": "scraping"},
    },
    # TradingView — ทุก 2 ชม.
    "scrape-tradingview": {
        "task": "app.tasks.news_tasks.scrape_source",
        "schedule": crontab(minute=15, hour="*/2"),
        "args": ["tradingview"],
        "options": {"queue": "scraping"},
    },
    # BabyPips — ทุก 2 ชม.
    "scrape-babypips": {
        "task": "app.tasks.news_tasks.scrape_source",
        "schedule": crontab(minute=30, hour="*/2"),
        "args": ["babypips"],
        "options": {"queue": "scraping"},
    },
    # Finviz — ทุก 1 ชม.
    "scrape-finviz": {
        "task": "app.tasks.news_tasks.scrape_source",
        "schedule": crontab(minute=45),
        "args": ["finviz"],
        "options": {"queue": "scraping"},
    },
    # Full pipeline — ทุก 1 ชม. (รวมทุก source + AI)
    "full-news-pipeline": {
        "task": "app.tasks.news_tasks.run_full_pipeline",
        "schedule": crontab(minute=0),
        "options": {"queue": "pipeline"},
    },
}

celery_app.autodiscover_tasks(["app.tasks"])
