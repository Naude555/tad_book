from datetime import datetime

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.db.models.signals import m2m_changed

from bookings.utils.generate_calendar_links import (
    generate_ics_file,
)
from bookings.utils.email_helpers import (
    generate_booking_notifications,
    generate_email_subject,
    get_admin_emails,
    get_recipient_list,
    prepare_calendar_event_details,
    prepare_email_context,
    update_context_with_calendar_details,
)
from .models import Bookings
from config.tasks import send_email_with_attachment


@receiver(m2m_changed, sender=Bookings.participants.through)
def notify_participants(sender, instance, action, reverse, model, pk_set, **kwargs):
    """
    Signal handler to notify participants when they are added or removed from a booking.

    Args:
        sender: The sender of the signal.
        instance: The instance of the Bookings model that triggered the signal.
        action: The type of action performed on the participants.
        reverse: A boolean indicating whether the relation is reversed.
        model: The model class of the participants.
        pk_set: The set of primary keys of the participants.
        **kwargs: Additional keyword arguments.

    Returns:
        None
    """
    booking = instance
    template = "email_templates/participant_notification.html"

    if action in ["post_add", "post_remove"]:
        participants = model.objects.filter(pk__in=pk_set)
        subject = (
            "You've been added to a booking"
            if action == "post_add"
            else "You've been removed from a booking"
        )
        message_body = "added to" if action == "post_add" else "removed from"

        for participant in participants:
            participant_name = (
                participant.get_full_name()
                if participant.is_active
                else participant.email
            )
            message = (
                f"Hello {participant_name},\n\nYou have been {message_body} a booking."
            )
            context = {
                "subject": subject,
                "message": message,
                "booking": booking,
            }
            if booking.status == "accepted" and action == "post_add":
                event_details = prepare_calendar_event_details(
                    booking,
                    context["message"],
                )
                context = update_context_with_calendar_details(context, event_details)
                ics_file_content = generate_ics_file(event_details)
                with open("booking_event.ics", "w") as ics_file:
                    ics_file.write(ics_file_content)

            if action == "post_remove":
                context["removed"] = True
            html_message = render_to_string(template, context)
            plain_message = strip_tags(html_message)

            # Send email to the participant
            send_email_with_attachment.delay(
                subject,
                plain_message,
                html_message,
                [participant.email],
                (
                    ics_file_content
                    if booking.status == "accepted" and action == "post_add"
                    else None
                ),
            )
            generate_booking_notifications(
                booking, [participant.email], subject, plain_message
            )


@receiver(post_save, sender=Bookings)
def send_booking_notification_email(sender, instance, created, **kwargs):
    """
    Signal handler to send booking notification emails.

    Args:
        sender: The sender of the signal.
        instance: The instance of the Bookings model that triggered the signal.
        created: A boolean indicating whether the instance was created or updated.
        **kwargs: Additional keyword arguments.

    Returns:
        None
    """
    booking = instance

    subject = generate_email_subject(booking)
    if not created:
        subject = f"Booking Updated for {booking.bookable_asset.asset.name} - {booking.bookable_asset.name} {subject}"

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
