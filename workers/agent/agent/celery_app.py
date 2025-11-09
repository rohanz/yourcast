from celery import Celery
from agent.config import settings

app = Celery(
    "yourcast-worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["agent.tasks"]
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    beat_schedule={
        'rss-discovery': {
            'task': 'rss_discovery',
            'schedule': 6 * 60 * 60,  # Every 6 hours (in seconds)
            'args': (20,),  # max_articles_per_feed
        },
    },
)

if __name__ == "__main__":
    app.start()