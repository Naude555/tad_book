import datetime
from typing import Optional
from accounts.models import Asset, AssetBookableHours, Config
from accounts.utils.date_time import get_weekday_num
from django.core.cache import cache

from bookings.models import Bookings, NoBookings
from django.db.models import Q


def calculate_slots(start_time, end_time, buffer_time, slot_duration):
    """Calculate the available slots between the given start and end times using the given buffer time and slot duration

    :param start_time: The start time.
    :param end_time: The end time.
    :param buffer_time: The buffer time.
    :param slot_duration: The duration of each slot.
    :return: A list of available slots.
    """
    slots = []
    buffer_time = buffer_time.replace(tzinfo=None)
    while start_time + slot_duration <= end_time:
        if start_time >= buffer_time:
            slots.append(start_time)
        start_time += slot_duration
    return slots


def check_no_bookings_day(asset_id, date) -> bool:
    """Check if the given asset_id is off on the given date.
    :param asset_id: The asset id to check.
    :param date: The date to check.
    """
    return NoBookings.objects.filter(
        asset=asset_id, start_date__lte=date, end_date__gte=date
    ).exists()


def is_in_bookable_time_frame(asset_id, target_date) -> bool:
    """
    Check if the target_date is within the bookable time frame for the given asset.

    Args:
    - asset: An instance of the Asset model with a days_ahead attribute.
    - target_date: A date object representing the date to check.

    Returns:
    - bool: True if the target_date is within the bookable time frame, False otherwise.
    """
    asset = Asset.objects.get(id=asset_id)
    # Ensure target_date is a date object
    if not isinstance(target_date, datetime.date):
        raise ValueError("target_date must be a datetime.date object")

    # Calculate the date range for bookable days
    if asset.max_days_ahead is not None and asset.max_days_ahead > 0:
        today = datetime.date.today()
        max_bookable_date = today + datetime.timedelta(days=asset.max_days_ahead)
        return today <= target_date <= max_bookable_date
    else:
        # If days_ahead is 0 or negative, assume no restriction on booking days ahead
        return True


def get_weekday_num_from_date(date: datetime.date = None) -> int:
    """Get the number of the weekday from the given date."""
    if date is None:
        date = datetime.date.today()
    return get_weekday_num(date.strftime("%A"))


def get_is_working_day(asset_id: int, day: int) -> bool:
    """Check if the given day is a working day for the staff member."""
    working_days = list(
        AssetBookableHours.objects.filter(asset=asset_id, is_active=True).values_list(
            "day_of_week", flat=True
        )
    )
    # return True  # TODO: Change this as this will return all days as a worknig day
    return day in working_days


def get_asset_buffer_time(asset: Asset, date: datetime.date) -> float:
    """Return the buffer time for the given staff member on the given date."""
    _, _, _, buff_time = get_times_from_config(date)
    buffer_minutes = buff_time.total_seconds() / 60
    return asset.buffer_time or buffer_minutes


def get_asset_slot_duration(asset: Asset, date: datetime.date) -> int:
    """Return the slot duration for the given staff member on the given date."""
    _, _, slot_duration, _ = get_times_from_config(date)
    slot_minutes = slot_duration.total_seconds() / 60
    return asset.slot_duration or slot_minutes


def get_working_hours_for_asset_and_day(asset_id, day_of_week):
    """Get the working hours for the given staff member and day of the week.

    :param staff_member: The staff member to get the working hours for.
    :param day_of_week: The day of the week to get the working hours for.
    :return: The working hours for the given staff member and day of the week.
    """
    working_hours = AssetBookableHours.objects.filter(
        asset=asset_id, day_of_week=day_of_week, is_active=True
    ).first()
    if not working_hours:
        return {
            "day_of_week": day_of_week,
            "start_time": Config.objects.first().get_start_time(),
            "end_time": Config.objects.first().get_end_time(),
        }

    # If a WorkingHours instance is found, convert it to a dictionary for consistent return type
    return {
        "day_of_week": working_hours.day_of_week,
        "start_time": working_hours.start_time,
        "end_time": working_hours.end_time,
    }


def calculate_bookable_asset_slots(date, bookable_asset):
    """Calculate the available slots for the given staff member on the given date.

    :param date: The date to calculate the slots for.
    :param staff_member: The staff member to calculate the slots for.
    :return: A list of available slots.
    """
    # Convert the times to datetime objects
    weekday_num = get_weekday_num_from_date(date)
    if not get_is_working_day(bookable_asset.asset.id, weekday_num):
        print("Is not worknig day")
        return []
    start_time = datetime.datetime.combine(
        date, get_asset_start_time(bookable_asset.asset, date)
    )
    end_time = datetime.datetime.combine(
        date, get_asset_end_time(bookable_asset.asset, date)
    )

    # Convert the buffer duration in minutes to a timedelta object
    buffer_duration_minutes = get_asset_buffer_time(bookable_asset.asset, date)
    buffer_duration = datetime.timedelta(minutes=buffer_duration_minutes)
    buffer_time_init = datetime.datetime.combine(date, start_time.time())
    buffer_time = buffer_time_init + buffer_duration
    print(buffer_time)

    # Convert slot duration to a timedelta object
    slot_duration_minutes = get_asset_slot_duration(bookable_asset.asset, date)
    slot_duration = datetime.timedelta(minutes=slot_duration_minutes)

    return calculate_slots(start_time, end_time, buffer_time, slot_duration)


def get_asset_start_time(asset: Asset, date: datetime.date) -> Optional[datetime.time]:
    """Return the start time for the given asset on the given date."""
    weekday_num = get_weekday_num_from_date(date)
    working_hours = get_working_hours_for_asset_and_day(asset.id, weekday_num)
    return working_hours["start_time"]


def get_asset_end_time(asset: Asset, date: datetime.date) -> Optional[datetime.time]:
    """Return the start time for the given asset on the given date."""
    weekday_num = get_weekday_num_from_date(date)
    working_hours = get_working_hours_for_asset_and_day(asset.id, weekday_num)
    return working_hours["end_time"]


def get_config():
    """Returns the configuration object from the database or the cache."""
    config = cache.get("config")
    if not config:
        config = Config.objects.first()
        # Cache the configuration for 1 hour (3600 seconds)
        cache.set("config", config, 3600)
    return config


def get_times_from_config(date):
    """Get the start time, end time, slot duration, and buffer time from the configuration or the settings file.

    :param date: The date to get the times for.
    :return: The start time, end time, slot duration, and buffer time.
    """
    config = get_config()
    if config:
        start_time = datetime.datetime.combine(
            date,
            datetime.time(hour=config.start_time.hour, minute=config.start_time.minute),
        )
        end_time = datetime.datetime.combine(
            date,
            datetime.time(hour=config.end_time.hour, minute=config.end_time.minute),
        )
        slot_duration = datetime.timedelta(minutes=config.slot_duration)
        buff_time = datetime.timedelta(minutes=config.buffer_time)
    else:
        start_hour, start_minute = (0, 0)
        start_time = datetime.datetime.combine(
            date, datetime.time(hour=start_hour, minute=start_minute)
        )
        finish_hour, finish_minute = (24, 00)
        end_time = datetime.datetime.combine(
            date, datetime.time(hour=finish_hour, minute=finish_minute)
        )
        slot_duration = datetime.timedelta(minutes=30)
        buff_time = datetime.timedelta(minutes=0)
    return start_time, end_time, slot_duration, buff_time


def get_bookings_for_date_and_time(date, start_time, end_time, bookable_asset):
    """Returns all appointments that overlap with the specified date and time range.

    :param date: The date to filter appointments on.
    :param start_time: The starting time to filter appointments on.
    :param end_time: The ending time to filter appointments on.
    :param staff_member: The staff member to filter appointments on.

    :return: QuerySet, all appointments that overlap with the specified date and time range
    """
    exclusive_booking_accross_organization = False
    exclusive_booking_accross_asset = False

    # A single bookable asset can not have a booking that overlaps

    if exclusive_booking_accross_organization:
        return Bookings.objects.filter(
            date=date,
            start_time__lte=end_time,
            end_time__gte=start_time,
            bookable_asset=bookable_asset,
            bookable_asset__asset__organization=bookable_asset.asset.organization,
        ).exclude(status__in=(["rejected", "canceled"]))

    if exclusive_booking_accross_asset:
        return Bookings.objects.filter(
            date=date,
            start_time__lte=end_time,
            end_time__gte=start_time,
            bookable_asset__asset=bookable_asset.asset,
        ).exclude(status__in=["rejected", "canceled"])

    return Bookings.objects.filter(
        date=date,
        start_time__lte=end_time,
        end_time__gte=start_time,
        bookable_asset=bookable_asset,
    ).exclude(status__in=["rejected", "canceled"])


def exclude_booked_slots(bookings, slots, slot_duration=None):

    available_slots = []
    for slot in slots:
        slot_end = slot + slot_duration
        is_available = True
        for booking in bookings:
            booking_start_time = booking.get_start_time()
            booking_end_time = booking.get_end_time()

            # Print out variables for debugging
            print(f"Slot: {slot.time()}")
            print(f"Slot End: {slot_end.time()}")
            print(f"Booking Start Time: {booking_start_time}")
            print(f"Booking End Time: {booking_end_time}")

            if booking_start_time < slot_end.time() and slot.time() < booking_end_time:
                print("false")
                is_available = False
                break
        if is_available:
            available_slots.append(slot)
    return available_slots
