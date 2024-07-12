import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from accounts.models import (
    Asset,
    BookableAsset,
    CustomUser,
    Organization,
    TimeStampedModel,
)
from accounts.utils.date_time import DAYS_OF_WEEK
from bookings.utils.booking_utils import BOOKING_STATUS_CHOICES

# Create your models here.


class Bookings(TimeStampedModel):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    bookable_asset = models.ForeignKey(BookableAsset, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=10, choices=BOOKING_STATUS_CHOICES, default="pending"
    )
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    participants = models.ManyToManyField(
        CustomUser, related_name="booking_participants", blank=True
    )
    notes = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.id:  # Only set default status on first save
            # Fetch the related asset's default appointment status
            default_status = self.bookable_asset.asset.default_booking_status
            self.status = default_status

        if self.bookable_asset.name == "Any" and self.status == "accepted":
            # This combination is not allowed status must default to pending as admin will have to change
            self.status = "pending"

        super().save(*args, **kwargs)

    def get_start_time(self):
        return self.start_time

    def get_end_time(self):
        return self.end_time

    def clean(self):  # Ensure start date is before end date
        if self.start_time > self.end_time:
            raise ValidationError(_("Start time must be before end time"))

    def remove_participant(self, user):
        try:
            self.participants.remove(user)
        except ObjectDoesNotExist:
            raise ValueError(f"The user {user} is not a participant of this booking.")

    class Meta:
        ordering = ["date", "start_time"]


class NoBookings(TimeStampedModel):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    description = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.start_date} to {self.end_date} - {self.description if self.description else 'Day off'}"

    def clean(self):
        # Ensure start date is not in the past
        if not self.id:
            if self.start_date < timezone.now().date():
                raise ValidationError(_("Start date cannot be in the past."))

        # Ensure start date is before end date
        if self.start_date > self.end_date:
            raise ValidationError(_("Start date must be before end date"))

        if self.id:  # For editing a no booking day
            # Check for existing bookings within the date range
            overlapping_bookings = Bookings.objects.filter(
                bookable_asset__asset=self.asset,
                date__range=(self.start_date, self.end_date),
                status="accepted",
            )
            print(overlapping_bookings)
            if overlapping_bookings.exists():
                raise ValidationError(
                    _("There are accepted bookings within the specified date range.")
                )

    def save(self, *args, **kwargs):
        # Call the clean method to run the validation logic
        self.clean()
        super().save(*args, **kwargs)


class BookingNotification(TimeStampedModel):
    booking = models.ForeignKey(Bookings, on_delete=models.CASCADE)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    sent = models.BooleanField(default=False)
    recipients = models.ManyToManyField(
        CustomUser, related_name="notification_recipients"
    )

    def __str__(self):
        return f"{self.subject}"

    class Meta:
        ordering = ["-id"]
