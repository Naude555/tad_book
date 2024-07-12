from django.db.models.signals import post_save, post_delete
from django.contrib.auth import get_user_model
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags

from accounts.models import Config, CustomUser, Membership
from config.tasks import send_email_with_attachment

from loguru import logger

logger.add("accounts_signals.log", rotation="500 MB")
logger.add("accounts_signals.log", rotation="1 week")


@receiver(post_save, sender=Membership)
def send_membership_notification_email(sender, instance, created, **kwargs):
    # Extract organization and asset details for the message and subject
    organization_name = instance.organization.name

    # Base message for the email body
    base_message = f"Membership for {organization_name}"

    # Helper function to generate the subject line based on booking status
    def get_subject():

        membership_subjects = {
            "pending": " - Pending",
            "invited": " - Invited",
            "accepted": " - Accepted",
        }
        # Get the status string from the dictionary, default to empty string if status not found
        status = membership_subjects.get(instance.status, "")
        return f"{status}"

    # Determine subject line: Differentiate between created and updated bookings
    subject = (
        f"Membership {get_subject()}"
        if created
        else f"Membership Updated {get_subject()}"
    )

    # Complete message for the email body
    message = f"{base_message}\n\n Status: {instance.status.capitalize()}"

    from_email = "noreply@example.com"
    user_recipient_list = [instance.user.email]

    # Get all admin users in the organization to include in recipient list
    admins = get_user_model().objects.filter(
        membership__organization_id=instance.organization,
        membership__role=Membership.ADMIN,
    )
    admin_emails = list(admins.values_list("email", flat=True))

    # Determine the email template and context based on booking status
    template = "email_templates/membership_notification.html"
    website_url = f"{Config.objects.get(pk=1).website_url}{reverse('accounts:login')}"
    logger.info(website_url)

    user_context = {
        "subject": subject,
        "message": message,
        "instance": instance,
        "website_url": website_url,
    }

    logger.info(f"Sending membership notification email to user: {user_recipient_list}")
    # Render the HTML email content for user
    user_html_message = render_to_string(template, user_context)
    # Convert HTML content to plain text for non-HTML email clients
    user_plain_message = strip_tags(user_html_message)

    # Send the email to the user
    send_email_with_attachment.delay(
        subject,
        user_plain_message,
        user_html_message,
        user_recipient_list,
    )

    # Prepare admin email content
    admin_subject = f"Admin Notification: {subject}"
    admin_message = f"Admin Notification:\n\n{message}"

    admin_context = {
        "subject": admin_subject,
        "message": admin_message,
        "instance": instance,
        "website_url": website_url,
    }

    # Render the HTML email content for admins
    admin_html_message = render_to_string(template, admin_context)
    # Convert HTML content to plain text for non-HTML email clients
    admin_plain_message = strip_tags(admin_html_message)

    # Send the email to the admins
    logger.info(f"Sending membership notification email to admins: {admin_emails}")
    send_email_with_attachment.delay(
        admin_subject,
        admin_plain_message,
        admin_html_message,
        admin_emails,
    )


@receiver(post_delete, sender=Membership)
def send_membership_deletion_notification_email(sender, instance, **kwargs):
    # Extract organization and asset details for the message and subject
    organization_name = instance.organization.name
    role = instance.role

    # Define subject and message
    subject = f"Membership Deleted: {organization_name}"
    message = f"Membership for {organization_name}\n\n Status: Deleted"

    user_recipient_list = instance.user.email

    # Get all admin users in the organization to include in recipient list
    admins = get_user_model().objects.filter(
        membership__organization_id=instance.organization,
        membership__role=Membership.ADMIN,
    )
    admin_emails = list(admins.values_list("email", flat=True))

    # Determine the email template and context
    template = "email_templates/membership_notification.html"
    website_url = f"{Config.objects.get(pk=1).website_url}{reverse('accounts:login')}"
    user_context = {
        "subject": subject,
        "message": message,
        "instance": instance,
        "website_url": website_url,
    }

    # Render the HTML email content for user
    user_html_message = render_to_string(template, user_context)
    # Convert HTML content to plain text for non-HTML email clients
    user_plain_message = strip_tags(user_html_message)

    # Send the email to the user
    send_email_with_attachment.delay(
        subject,
        user_plain_message,
        user_html_message,
        [user_recipient_list],
    )

    # Prepare admin email content
    admin_subject = f"Admin Notification: {subject}"
    admin_message = f"Admin Notification:\n\n{message}"

    admin_context = {
        "subject": admin_subject,
        "message": admin_message,
        "instance": instance,
        "website_url": website_url,
    }

    # Render the HTML email content for admins
    admin_html_message = render_to_string(template, admin_context)
    # Convert HTML content to plain text for non-HTML email clients
    admin_plain_message = strip_tags(admin_html_message)

    # Send the email to the admins
    send_email_with_attachment.delay(
        admin_subject,
        admin_plain_message,
        admin_html_message,
        admin_emails,
    )


@receiver(post_save, sender=CustomUser)
def send_invitation_notification_email(sender, instance, created, **kwargs):
    if created:
        email = instance.email
        is_active = instance.is_active
        invitation_token = instance.username

        if not is_active:

            # Determine subject line: Differentiate between created and updated bookings
            subject = "You were invited to claim an account on TAD Book"

            # Complete message for the email body
            message = "You received this message because you were added as a participant to a booking or as a member to an organization."
            website_url = (
                f"{Config.objects.get(pk=1).website_url}{reverse('accounts:login')}"
            )
            invitation_url = f"{website_url}{reverse('accounts:claim_account', args=[invitation_token])}"
            logger.info(invitation_url)

            from_email = "noreply@example.com"
            user_recipient_list = email

            template = "email_templates/invitation_email.html"

            user_context = {
                "subject": subject,
                "message": message,
                "instance": instance,
                "invitation_url": invitation_url,
                "website_url": website_url,
            }

            # Render the HTML email content for user
            user_html_message = render_to_string(template, user_context)
            # Convert HTML content to plain text for non-HTML email clients
            user_plain_message = strip_tags(user_html_message)

            # Print for debugging (optional)
            print(subject, message, from_email, user_recipient_list)

            # Send the email to the user
            send_email_with_attachment.delay(
                subject,
                user_plain_message,
                user_html_message,
                [user_recipient_list],
            )
