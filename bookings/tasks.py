from datetime import date, timedelta, datetime
from celery import shared_task
from bookings.utils.email_helpers import (
    generate_booking_notifications,
    get_admin_emails,
    get_recipient_list,
    prepare_calendar_event_details,
    prepare_email_context,
    update_context_with_calendar_details,
)
from config.tasks import send_email_with_attachment
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from loguru import logger
import pytz

from bookings.utils.generate_calendar_links import generate_ics_file
from accounts.utils.date_time import get_current_time

from .models import Bookings
from django.contrib.auth.models import User
from .models import BookingNotification
from django.utils import timezone

logger.add("bookings_celery_beat.log", rotation="500 MB")
logger.add("bookings_celery_beat.log", rotation="1 week")


@shared_task
def send_reminder_email_booking_still_pending():
    "send an email if a booking was created more than 24 hours ago and is still pending and is still in the Future"
    bookings = Bookings.objects.filter(
        status="pending",
        create_datetime__lte=datetime.now(pytz.timezone("Africa/Johannesburg")),
        date__gte=date.today(),
    )
    for booking in bookings:
        if booking.create_datetime < datetime.now(
            pytz.timezone("Africa/Johannesburg")
        ) - timedelta(days=1):
            subject = "Booking still pending after 24 hours"
            admin_emails = get_admin_emails(booking)
            admin_context = prepare_email_context(booking, subject, is_admin=True)
            template = "email_templates/booking_notification.html"

            admin_html_message = render_to_string(template, admin_context)
            admin_plain_message = strip_tags(admin_html_message)

            # Send email to admins
            send_email_with_attachment.delay(
                admin_context["subject"],
                admin_plain_message,
                admin_html_message,
                admin_emails,
                None,
            )
            generate_booking_notifications(
                booking, admin_emails, subject, admin_plain_message
            )

            # Log the booking details
            logger.info(f"Reminder email sent for booking pending {booking.id}")


@shared_task
def send_reminder_email_booking_today():
    "send an email if a booking is today"
    bookings = Bookings.objects.filter(status="accepted", date=date.today())
    for booking in bookings:
        subject = "Booking Reminder Today"
        template = "email_templates/booking_notification.html"
        ics_file_content = None

        # non admin recipients
        non_admin_context = prepare_email_context(booking, subject)
        if booking.status == "accepted":
            event_details = prepare_calendar_event_details(
                booking, non_admin_context["message"]
            )
            non_admin_context = update_context_with_calendar_details(
                non_admin_context, event_details
            )
            ics_file_content = generate_ics_file(event_details)
            with open("booking_event.ics", "w") as ics_file:
                ics_file.write(ics_file_content)

        non_admin_html_message = render_to_string(template, non_admin_context)
        non_admin_plain_message = strip_tags(non_admin_html_message)

        recipient_list = get_recipient_list(booking)
        # Send email to non-admin recipients
        send_email_with_attachment.delay(
            subject,
            non_admin_plain_message,
            non_admin_html_message,
            recipient_list,
            ics_file_content if booking.status == "accepted" else None,
        )
        generate_booking_notifications(
            booking, recipient_list, subject, non_admin_plain_message
        )

        # admin recipients
        admin_context = prepare_email_context(booking, subject, is_admin=True)
        if booking.status == "accepted":
            event_details = prepare_calendar_event_details(
                booking, admin_context["message"]
            )
            admin_context = update_context_with_calendar_details(
                admin_context, event_details
            )
            ics_file_content = generate_ics_file(event_details)
            with open("booking_event.ics", "w") as ics_file:
                ics_file.write(ics_file_content)

        admin_html_message = render_to_string(template, admin_context)
        admin_plain_message = strip_tags(admin_html_message)

        admin_recipient_list = get_admin_emails(booking)
        # Send email to admin recipients
        send_email_with_attachment.delay(
            admin_context["subject"],
            admin_plain_message,
            admin_html_message,
            admin_recipient_list,
            ics_file_content if booking.status == "accepted" else None,
        )
        generate_booking_notifications(
            booking, admin_recipient_list, subject, admin_plain_message
        )
        logger.info(f"Reminder email sent for booking today {booking.id}")


@shared_task
def send_reminder_email_booking_in_30_min():
    "send an email if a booking is in 30 minutes"
    now = datetime.now(pytz.timezone("Africa/Johannesburg"))
    logger.info(now.time())
    current_time = now.time()
    thirty_min_time = (now + timedelta(minutes=30)).time()
    logger.info(now + timedelta(minutes=30))
    subject = "Booking starting in 30 minutes"
    template = "email_templates/booking_notification.html"
    bookings = Bookings.objects.filter(
        status="accepted",
        date=date.today(),
        start_time__gte=current_time,
        start_time__lte=thirty_min_time,
    ).exclude(
        id__in=BookingNotification.objects.filter(subject=subject).values_list(
            "booking", flat=True
        )
    )
    for booking in bookings:
        logger.info(booking)
        ics_file_content = None

        # non admin recipients
        non_admin_context = prepare_email_context(booking, subject)
        if booking.status == "accepted":
            event_details = prepare_calendar_event_details(
                booking, non_admin_context["message"]
            )
            non_admin_context = update_context_with_calendar_details(
                non_admin_context, event_details
            )
            ics_file_content = generate_ics_file(event_details)
            with open("booking_event.ics", "w") as ics_file:
                ics_file.write(ics_file_content)

        non_admin_html_message = render_to_string(template, non_admin_context)
        non_admin_plain_message = strip_tags(non_admin_html_message)
        non_admin_recipients = get_recipient_list(booking)
        # Send email to non-admin recipients
        send_email_with_attachment.delay(
            subject,
            non_admin_plain_message,
            non_admin_html_message,
            non_admin_recipients,
            ics_file_content if booking.status == "accepted" else None,
        )
        generate_booking_notifications(
            booking, non_admin_recipients, subject, non_admin_plain_message
        )

        # admin recipients
        admin_context = prepare_email_context(booking, subject, is_admin=True)
        if booking.status == "accepted":
            event_details = prepare_calendar_event_details(
                booking, admin_context["message"]
            )
            admin_context = update_context_with_calendar_details(
                admin_context, event_details
            )
            ics_file_content = generate_ics_file(event_details)
            with open("booking_event.ics", "w") as ics_file:
                ics_file.write(ics_file_content)

        admin_html_message = render_to_string(template, admin_context)
        admin_plain_message = strip_tags(admin_html_message)
        # Get the admin emails for the booking
        admin_emails = get_admin_emails(booking)

        # Send email to admin recipients
        send_email_with_attachment.delay(
            admin_context["subject"],
            admin_plain_message,
            admin_html_message,
            admin_emails,
            ics_file_content if booking.status == "accepted" else None,
        )
        generate_booking_notifications(
            booking, admin_emails, subject, admin_plain_message
        )
        logger.info(f"Reminder email sent for booking starting in 30 {booking.id}")
