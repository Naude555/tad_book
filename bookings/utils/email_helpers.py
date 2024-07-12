from datetime import datetime
from django.contrib.auth import get_user_model
from django.urls import reverse
from accounts.models import Config, CustomUser, Membership
from bookings.utils.generate_calendar_links import (
    generate_google_calendar_url,
    generate_outlook_calendar_url,
    generate_yahoo_calendar_url,
)
from bookings.models import BookingNotification


def generate_email_subject(booking):
    base_subject = f"Booking @ {booking.bookable_asset.asset.organization.name}"
    status_subjects = {
        "pending": " - Pending",
        "rejected": " - Rejected",
        "accepted": " - Accepted",
        "canceled": " - Canceled",
    }
    status_suffix = status_subjects.get(booking.status, "")
    subject = f"{base_subject}{status_suffix}"

    return subject


def prepare_email_context(booking, subject, is_admin=False):
    base_context = {
        "subject": subject,
        "message": "\n\n",
        "booking": booking,
    }
    website_url = Config.objects.get(pk=1).website_url
    if is_admin:
        base_context.update(
            {
                "subject": f"Admin Notification: {subject}",
                "approval_url": f"{website_url}{reverse('bookings:approve_booking', args=[booking.id, booking.token])}",
                "reject_url": f"{website_url}{reverse('bookings:reject_booking', args=[booking.id, booking.token])}",
            }
        )
    else:
        base_context.update(
            {
                "cancel_url": f"{website_url}{reverse('bookings:cancel_booking', args=[booking.id, booking.token])}",
            }
        )
    return base_context


def update_context_with_calendar_details(context, event_details):
    context["google_calendar_url"] = generate_google_calendar_url(event_details)
    context["outlook_calendar_url"] = generate_outlook_calendar_url(event_details)
    context["yahoo_calendar_url"] = generate_yahoo_calendar_url(event_details)

    return context


def prepare_calendar_event_details(booking, message):
    return {
        "start": datetime.combine(booking.date, booking.start_time),
        "end": datetime.combine(booking.date, booking.end_time),
        "title": f"Booking for {booking.bookable_asset.name}",
        "description": message,
        "location": booking.bookable_asset.asset.organization.name,
        "allDay": False,
        "busy": True,
        "guests": [booking.user.email]
        + list(booking.participants.values_list("email", flat=True)),
        "rRule": None,
    }


def get_admin_emails(booking):
    admins = get_user_model().objects.filter(
        membership__organization_id=booking.bookable_asset.asset.organization,
        membership__role=Membership.ADMIN,
    )
    admin_emails = list(admins.values_list("email", flat=True))
    return admin_emails


def get_recipient_list(booking):
    user_recipient_list = [booking.user.email]
    participant_emails = list(booking.participants.values_list("email", flat=True))
    non_admin_recipients = user_recipient_list + participant_emails
    return non_admin_recipients


def generate_booking_notifications(booking, recipient_list, subject, plain_message):
    # Create the BookingNotification instance
    booking_notification = BookingNotification.objects.create(
        booking=booking, subject=subject, message=plain_message, sent=False
    )

    # Fetch users based on recipient emails
    recipients = CustomUser.objects.filter(email__in=recipient_list)

    # Add recipients to the booking notification
    booking_notification.recipients.add(*recipients)

    # Save the booking notification instance
    booking_notification.save()
