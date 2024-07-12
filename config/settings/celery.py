import os
from celery.schedules import crontab

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_BACKEND", "redis://redis:6379/0")

CELERY_BEAT_SCHEDULE = {
    "booking_still_pending": {
        "task": "bookings.tasks.send_reminder_email_booking_still_pending",
        "schedule": crontab(
            # minute="*/2"
            hour="10-19",
            minute="*/60",
        ),  # Cerery beat uses std time and should be taken into account
    },
    "booking_today": {
        "task": "bookings.tasks.send_reminder_email_booking_today",
        "schedule": crontab(
            # minute="*/2"
            minute=0,
            hour=9,
        ),  # Cerery beat uses std time and should be taken into account
    },
    "booking_in_30_min": {
        "task": "bookings.tasks.send_reminder_email_booking_in_30_min",
        "schedule": crontab(
            minute="*/5"
        ),  # Cerery beat uses std time and should be taken into account
    },
}
