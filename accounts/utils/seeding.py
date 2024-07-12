from accounts.models import AssetBookableHours, BookableAsset


def seed_bookable_hours(asset):
    # Define standard bookable hours (example: 9 AM to 5 PM for each weekday)
    standard_hours = [
        {
            "day_of_week": 1,
            "start_time": "08:00",
            "end_time": "17:00",
            "is_active": True,
        },  # Monday
        {
            "day_of_week": 2,
            "start_time": "08:00",
            "end_time": "17:00",
            "is_active": True,
        },  # Tuesday
        {
            "day_of_week": 3,
            "start_time": "08:00",
            "end_time": "17:00",
            "is_active": True,
        },  # Wednesday
        {
            "day_of_week": 4,
            "start_time": "08:00",
            "end_time": "17:00",
            "is_active": True,
        },  # Thursday
        {
            "day_of_week": 5,
            "start_time": "08:00",
            "end_time": "17:00",
            "is_active": True,
        },  # Friday
        {
            "day_of_week": 6,
            "start_time": "08:00",
            "end_time": "17:00",
            "is_active": False,
        },  # Saturday
        {
            "day_of_week": 0,
            "start_time": "08:00",
            "end_time": "17:00",
            "is_active": False,
        },  # Sunday
    ]

    # Create bookable hours for the asset
    for hours in standard_hours:
        AssetBookableHours.objects.create(
            asset=asset,
            day_of_week=hours["day_of_week"],
            start_time=hours["start_time"],
            end_time=hours["end_time"],
            is_active=hours["is_active"],
        )


def seed_any_bookable_asset(asset):
    BookableAsset.objects.create(asset=asset, name="Any")
