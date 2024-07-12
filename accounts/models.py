from datetime import date
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify
import uuid
from phonenumber_field.modelfields import PhoneNumberField
from django.db.models import Q

from django.utils.translation import gettext_lazy as _

import zoneinfo

from accounts.utils.date_time import (
    DAYS_OF_WEEK,
    convert_minutes_in_human_readable_format,
    get_current_time,
)

from bookings.utils.booking_utils import BOOKING_STATUS_CHOICES


class TimeStampedModel(models.Model):
    create_datetime = models.DateTimeField(auto_now_add=True, editable=False)
    update_datetime = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


TIMEZONES_CHOICES = [(tz, tz) for tz in zoneinfo.available_timezones()]


class CustomUser(TimeStampedModel, AbstractUser):
    username = models.CharField(unique=True, max_length=50)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    bio = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=30, blank=True, null=True)
    birth_date = models.DateField(null=True, blank=True)
    slug = models.SlugField(unique=True)
    phone = PhoneNumberField(blank=True)
    can_start_own_organizations = models.BooleanField(default=False)
    timezone = models.CharField(
        max_length=50,
        default="Africa/Johannesburg",
        choices=TIMEZONES_CHOICES,
    )

    def save(self, *args, **kwargs):
        # Check if the object is being created or updated
        if not self.id:  # Object is being created
            self.slug = self.generate_unique_slug()
        else:  # Object is being updated
            old_first_name = CustomUser.objects.filter(pk=self.pk).first().first_name
            if old_first_name in [None, ""] and self.first_name not in [None, ""]:
                self.slug = self.generate_unique_slug()
            if self.slug == "" or self.slug.startswith("invited-user"):
                self.slug = self.generate_unique_slug()

        super().save(*args, **kwargs)

    def generate_unique_slug(self):
        base_slug = slugify(self.first_name)
        if base_slug == "":
            base_slug = slugify("invited-user")
        slug = base_slug
        counter = 1
        while CustomUser.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    def __str__(self):
        return self.username

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"


class Organization(TimeStampedModel):
    name = models.CharField(max_length=255)
    asset_name = models.CharField(max_length=25, blank=True, null=True, default="Asset")
    members = models.ManyToManyField(
        CustomUser, through="Membership", related_name="organizations"
    )
    slug = models.SlugField(unique=True)
    exclusive_booking_accross_organization = models.BooleanField(
        default=False,
        help_text="An Organization can only accept one booking for a timeslot",
    )
    exclusive_booking_accross_asset = models.BooleanField(
        default=False, help_text="An Asset can only accept one booking for a timeslot"
    )

    def clean(self):
        if (
            self.exclusive_booking_accross_organization == True
            and self.exclusive_booking_accross_asset == False
        ):
            raise ValidationError(
                _(
                    "Exclusive booking for assets can not be False if Exclusive booking for organization is True"
                )
            )

    def save(self, *args, **kwargs):
        # Ensure name starts with a capital letter
        if self.name:
            self.name = self.name.capitalize()

        if self.asset_name:
            self.asset_name = self.asset_name.capitalize()

        if not self.id:  # Generate slug only if object is being created
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Organization.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def total_members_count(self):
        return self.membership_set.all().count()

    def pending_members_count(self):
        return self.membership_set.filter(status__in=["pending", "invited"]).count()

    def invited_members_count(self):
        return self.membership_set.filter(status="invited").count()

    def requested_members_count(self):
        return self.membership_set.filter(status="pending").count()


class Membership(TimeStampedModel):
    MEMBER = "member"
    ADMIN = "admin"
    ROLE_CHOICES = [
        (MEMBER, "Member"),
        (ADMIN, "Admin"),
    ]
    INVITATION_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("invited", "Invited"),
        ("accepted", "Accepted"),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=MEMBER)
    is_approved = models.BooleanField(default=False)
    status = models.CharField(
        max_length=10, choices=INVITATION_STATUS_CHOICES, default="pending"
    )

    class Meta:
        unique_together = ("user", "organization")

    def __str__(self):
        return f"{self.user.username} - {self.organization.name} ({self.get_role_display()})"

    def is_admin(self, user):
        return Membership.objects.filter(
            user=user, organization=self.organization, role=self.ADMIN
        ).exists()


class Config(models.Model):

    slot_duration = models.PositiveIntegerField(
        null=True,
        help_text=_("Minimum time for an appointment in minutes, recommended 30."),
        default="30",
    )
    start_time = models.TimeField(
        null=True,
        help_text=_("Time when we start working."),
        default="08:00",
    )
    end_time = models.TimeField(
        null=True,
        help_text=_("Time when we stop working."),
        default="17:00",
    )
    buffer_time = models.FloatField(
        null=True,
        help_text=_(
            "Time between now and the first available slot for the current day (doesn't affect tomorrow)."
        ),
        default="15",
    )
    website_name = models.CharField(
        max_length=255,
        default="",
        help_text=_("Name of your website."),
    )
    website_url = models.CharField(
        max_length=255,
        default="",
        help_text=_("URL of your website."),
    )
    app_offered_by_label = models.CharField(
        max_length=255,
        default=_("Offered by"),
        help_text=_("Label for `Offered by` on the appointment page"),
    )

    def clean(self):
        if Config.objects.exists() and not self.pk:
            raise ValidationError(_("You can only create one Config object"))
        if self.start_time is not None and self.end_time is not None:
            if self.start_time >= self.end_time:
                raise ValidationError(_("Lead time must be before finish time"))
        if self.buffer_time is not None and self.buffer_time < 0:
            raise ValidationError(_("Appointment buffer time cannot be negative"))
        if self.slot_duration is not None and self.slot_duration <= 0:
            raise ValidationError(_("Slot duration must be greater than 0"))

    def save(self, *args, **kwargs):
        self.clean()
        self.pk = 1
        super(Config, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def get_instance(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return (
            f"Config {self.pk}: slot_duration={self.slot_duration}, start_time={self.start_time}, "
            f"end_time={self.end_time}"
        )

    def get_start_time(self):
        return self.start_time

    def get_end_time(self):
        return self.end_time


class Asset(TimeStampedModel):

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="Assets"
    )
    name = models.CharField(max_length=255)
    bookable_asset_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        default="Bookable Asset",
        help_text="What do you want to call your bookable assets?",
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of what you are booking when booking something from this asset class.",
    )
    slug = models.SlugField(unique=True)
    default_booking_status = models.CharField(
        max_length=10,
        choices=BOOKING_STATUS_CHOICES,
        default="pending",
        help_text="When someone makes a booking this will be the default status.",
    )
    slot_duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Minimum time for an appointment in minutes, recommended 30."),
        default="30",
    )
    buffer_time = models.FloatField(
        blank=True,
        null=True,
        help_text=_(
            "Time between now and the first available slot for the current day."
        ),
    )
    max_days_ahead = models.IntegerField(
        null=True,
        blank=True,
        help_text="How many days ahead do you want to allow bookings?",
    )
    admin_assigns_booking = models.BooleanField(
        default=False,
        help_text="Only admins can assign bookable asset to users",
    )

    def save(self, *args, **kwargs):
        # Ensure name starts with a capital letter
        if self.name:
            self.name = self.name.capitalize()

        # Ensure bookable_asset_name starts with a capital letter if it is set
        if self.bookable_asset_name:
            self.bookable_asset_name = self.bookable_asset_name.capitalize()

        if not self.id:  # Generate slug only if object is being created
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Asset.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.organization.name})"

    def total_bookable_assets(self):
        return self.bookable_assets.count()

    def get_slot_duration(self):
        config = Config.objects.first()
        return self.slot_duration or (config.slot_duration if config else 0)

    def get_slot_duration_text(self):
        slot_duration = self.get_slot_duration()
        return convert_minutes_in_human_readable_format(slot_duration)


class BookableAsset(TimeStampedModel):
    asset = models.ForeignKey(
        Asset, on_delete=models.CASCADE, related_name="bookable_assets"
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    calendar_colour = models.CharField(max_length=7, default="#6590D5")
    share_link = models.BooleanField(
        default=False,
        help_text="Allow users to share the link to this bookable asset to see bookings",
    )

    def save(self, *args, **kwargs):

        # Ensure name starts with a capital letter
        if self.name:
            self.name = self.name[0].upper() + self.name[1:]

        if not self.id:  # Generate slug only if object is being created
            base_slug = slugify(self.name)
            if self.name == "Any":
                base_slug = f"{slugify(self.asset.name)}-any"
            print(base_slug)
            slug = base_slug
            counter = 1
            while BookableAsset.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
            print(slug)
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ("asset", "name")

    def __str__(self):
        return f"{self.name} ({self.asset.name})"

    def get_absolute_url(self) -> str:
        return reverse("accounts:bookable_assets", kwargs={"asset_id": self.asset.id})


class AssetBookableHours(TimeStampedModel):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    day_of_week = models.PositiveIntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return (
            f"{self.get_day_of_week_display()} - {self.start_time} to {self.end_time}"
        )

    def status(self):
        return "Active" if self.is_active else "Disabled"

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError("Start time must be before end time")

    def get_start_time(self):
        return self.start_time

    def get_end_time(self):
        return self.end_time

    def get_day_of_week_str(self):
        # return the name of the day instead of the integer
        return self.get_day_of_week_display()

    def delete(self, *args, **kwargs):
        raise ValidationError("Deletion of AssetBookableHours instances is not allowed")

    class Meta:
        unique_together = ["asset", "day_of_week"]
