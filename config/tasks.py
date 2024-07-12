import tempfile
from django.core.mail import send_mail, EmailMultiAlternatives
from celery import shared_task


@shared_task
def send_email_with_attachment(
    subject, plain_message, html_message, recipient_list, attachment=None
):

    from_email = "support@tad.co.za"
    if not isinstance(recipient_list, list):
        recipient_list = [recipient_list]
    # Send the email
    email = EmailMultiAlternatives(subject, plain_message, from_email, recipient_list)
    email.attach_alternative(html_message, "text/html")

    if attachment:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ics") as ics_file:
            ics_file.write(attachment.encode())
            ics_file.seek(0)
            email.attach("booking_event.ics", ics_file.read(), "text/calendar")

    email.send(fail_silently=False)
