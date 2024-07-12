import datetime

from django.shortcuts import get_object_or_404

from accounts.models import Asset, BookableAsset
from bookings.utils.db_helpers import (
    calculate_bookable_asset_slots,
    check_no_bookings_day,
    exclude_booked_slots,
    get_bookings_for_date_and_time,
    get_weekday_num_from_date,
    get_working_hours_for_asset_and_day,
)


def get_available_slots_for_bookable_asset(bookable_asset_id, date):
    bookable_asset = get_object_or_404(BookableAsset, id=bookable_asset_id)
    # Check if the provided date is a day off for the staff member
    days_off_exist = check_no_bookings_day(asset_id=bookable_asset.asset.id, date=date)
    print(f"days_off_exist: {days_off_exist} ")
    if days_off_exist:
        return []

    # Check if the staff member works on the provided date
    day_of_week = get_weekday_num_from_date(
        date
    )  # Python's weekday starts from Monday (0) to Sunday (6)
    print(f"day of week: {day_of_week}")
    working_hours_dict = get_working_hours_for_asset_and_day(
        bookable_asset.asset.id, day_of_week
    )
    print(f"working hours dict: {working_hours_dict}")
    if not working_hours_dict:
        return []

    slot_duration = datetime.timedelta(minutes=bookable_asset.asset.get_slot_duration())
    print(f"slot_duration: {slot_duration}")
    slots = calculate_bookable_asset_slots(date, bookable_asset)
    print(f"slots: {slots}")

    if bookable_asset.name == "Any":
        all_available_bookings = []
        all_bookable_assets = BookableAsset.objects.filter(
            asset=bookable_asset.asset
        ).exclude(name="Any")
        for bookable_asset in all_bookable_assets:
            bookings = get_bookings_for_date_and_time(
                date,
                working_hours_dict["start_time"],
                working_hours_dict["end_time"],
                bookable_asset,
            )
            all_available_bookings.extend(
                exclude_booked_slots(bookings, slots, slot_duration)
            )

        # Remove duplicates
        all_available_bookings = list(set(all_available_bookings))

        # Sort the list
        all_available_bookings.sort()

        return all_available_bookings

    bookings = get_bookings_for_date_and_time(
        date,
        working_hours_dict["start_time"],
        working_hours_dict["end_time"],
        bookable_asset,
    )
    print(f"bookings {bookings}")
    return exclude_booked_slots(bookings, slots, slot_duration)
