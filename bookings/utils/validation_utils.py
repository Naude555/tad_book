from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from bookings.utils.booking_utils import reject_bookings
from bookings.utils.db_helpers import (
    check_no_bookings_day,
    get_bookings_for_date_and_time,
    get_is_working_day,
    get_weekday_num_from_date,
)


def validate_booking(booking, form):
    has_error = False

    # Check for any existing bookings on the specified date
    if check_no_bookings_day(
        asset_id=booking.bookable_asset.asset.id, date=booking.date
    ):
        form.add_error(
            None,
            ValidationError(_("No bookings are accepted for this date")),
        )
        has_error = True

    # Check if the specified date is a working day
    weekday_num = get_weekday_num_from_date(booking.date)
    if not get_is_working_day(
        asset_id=booking.bookable_asset.asset.id, day=weekday_num
    ):
        form.add_error(
            None,
            ValidationError(
                _("The specified date is not a working day for this asset.")
            ),
        )
        has_error = True

    # Fetch all overlapping bookings
    overlapping_bookings = get_bookings_for_date_and_time(
        booking.date, booking.start_time, booking.end_time, booking.bookable_asset
    )

    # Check for overlapping accepted bookings
    overlapping_accepted_bookings = overlapping_bookings.filter(
        status="accepted"
    ).exclude(id=booking.id)
    print(overlapping_accepted_bookings)
    if overlapping_accepted_bookings.exists():
        form.add_error(
            None,
            ValidationError(
                _(
                    "There are existing accepted bookings that overlap with the specified time range."
                )
            ),
        )
        has_error = True
    else:
        # Handle non-accepted overlapping bookings
        overlapping_non_accepted_bookings = overlapping_bookings.exclude(
            status="accepted"
        ).exclude(id=booking.id)

        if overlapping_non_accepted_bookings.exists():
            reject_bookings(overlapping_non_accepted_bookings)

    if booking.bookable_asset.name == "Any" and booking.status == "accepted":
        form.add_error(
            None,
            ValidationError(
                _(
                    "The booking status cannot be accepted for a bookable asset named 'Any', Please assign."
                )
            ),
        )
        has_error = True

    return has_error
