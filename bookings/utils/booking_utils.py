BOOKING_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("rejected", "Rejected"),
    ("accepted", "Accepted"),
    ("canceled", "Canceled"),
]


def cancel_bookings(bookings):
    for booking in bookings:
        booking.status = "cancelled"
        booking.save()


def reject_bookings(bookings):
    for booking in bookings:
        booking.status = "rejected"
        booking.save()
