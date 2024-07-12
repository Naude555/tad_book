import pytz
from datetime import datetime, timedelta
from urllib.parse import urlencode
import uuid


def format_event_dates(event, format_key):
    format_map = {
        "allDay": "%Y%m%d",
        "dateTimeUTC": "%Y%m%dT%H%M%SZ",
        "dateTimeLocal": "%Y%m%dT%H%M%S",
    }
    date_format = format_map[format_key]
    return {
        "start": event["startTime"].strftime(date_format),
        "end": event["endTime"].strftime(date_format),
    }


def format_event_dates_outlook(event, format_key):
    format_map = {
        "allDay": "%Y-%m-%d",
        "dateTimeUTC": "%Y-%m-%dT%H:%M:%SZ",
        "dateTimeLocal": "%Y-%m-%dT%H:%M:%S",
    }
    date_format = format_map[format_key]
    return {
        "start": event["startTime"].strftime(date_format),
        "end": event["endTime"].strftime(date_format),
    }


def transform_event(event, use_utc=True):
    start = event.get("start")
    end = event.get("end")
    duration = event.get("duration")

    def exclude_keys(dictionary, keys):
        return {k: v for k, v in dictionary.items() if k not in keys}

    event_metadata = exclude_keys(event, ["start", "end", "duration"])

    if use_utc:
        start_time = start.astimezone(pytz.UTC)
    else:
        start_time = start

    if end:
        end_time = end.astimezone(pytz.UTC) if use_utc else end
    else:
        if event.get("allDay"):
            end_time = start_time + timedelta(days=1)
        elif duration and len(duration) == 2:
            duration_value = int(duration[0])
            end_time = start_time + timedelta(**{duration[1]: duration_value})
        else:
            end_time = datetime.now(datetime.UTC) if use_utc else datetime.now()

    return {**event_metadata, "startTime": start_time, "endTime": end_time}


def generate_google_calendar_url(event):
    transformed_event = transform_event(event)
    formatted_times = format_event_dates(
        transformed_event,
        "allDay" if transformed_event.get("allDay") else "dateTimeUTC",
    )
    start_date, end_date = formatted_times["start"], formatted_times["end"]

    calendar_event = {
        "action": "TEMPLATE",
        "text": transformed_event.get("title"),
        "details": transformed_event.get("description"),
        "location": transformed_event.get("location"),
        "trp": transformed_event.get("busy"),
        "dates": f"{start_date}/{end_date}",
        "recur": (
            f"RRULE:{transformed_event.get('rRule')}"
            if transformed_event.get("rRule")
            else None
        ),
    }

    if transformed_event.get("guests"):
        calendar_event["add"] = ",".join(transformed_event["guests"])

    return f"https://calendar.google.com/calendar/render?{urlencode(calendar_event)}"


def generate_outlook_calendar_url(event):
    transformed_event = transform_event(event, use_utc=False)
    formatted_times = format_event_dates_outlook(transformed_event, "dateTimeLocal")
    start_date, end_date = formatted_times["start"], formatted_times["end"]

    params = {
        "path": "/calendar/action/compose",
        "rru": "addevent",
        "startdt": start_date,
        "enddt": end_date,
        "subject": transformed_event.get("title"),
        "body": transformed_event.get("description"),
        "location": transformed_event.get("location"),
        "allday": transformed_event.get("allDay", False),
    }

    return f"https://outlook.live.com/calendar/0/action/compose?{urlencode(params)}"


def generate_yahoo_calendar_url(event):
    transformed_event = transform_event(event)
    formatted_times = format_event_dates(
        transformed_event,
        "allDay" if transformed_event.get("allDay") else "dateTimeUTC",
    )
    start_date, end_date = formatted_times["start"], formatted_times["end"]

    params = {
        "v": 60,
        "title": transformed_event.get("title"),
        "st": start_date,
        "et": end_date,
        "desc": transformed_event.get("description"),
        "in_loc": transformed_event.get("location"),
        "dur": "allday" if transformed_event.get("allDay") else None,
    }

    return f"https://calendar.yahoo.com/?{urlencode(params)}"


def generate_ics_file(event):
    transformed_event = transform_event(event)
    uid = uuid.uuid4()
    dtstamp = datetime.now(pytz.UTC).strftime("%Y%m%dT%H%M%SZ")
    formatted_times = format_event_dates(transformed_event, "dateTimeUTC")
    start_date, end_date = formatted_times["start"], formatted_times["end"]

    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//YourProduct//YourApp//EN
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{dtstamp}
DTSTART:{start_date}
DTEND:{end_date}
SUMMARY:{transformed_event.get("title")}
DESCRIPTION:{transformed_event.get("description")}
LOCATION:{transformed_event.get("location")}
STATUS:CONFIRMED
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR"""

    return ics_content


# Example usage to generate a .ics file
event = {
    "start": datetime(2024, 7, 1, 10, 0, 0, tzinfo=pytz.UTC),
    "end": datetime(2024, 7, 1, 12, 0, 0, tzinfo=pytz.UTC),
    "title": "Meeting",
    "description": "Discuss project updates",
    "location": "Conference Room",
    "allDay": False,
    "busy": True,
    "guests": ["guest1@example.com", "guest2@example.com"],
    "rRule": "FREQ=DAILY;COUNT=5",
}

ics_file_content = generate_ics_file(event)
with open("event.ics", "w") as file:
    file.write(ics_file_content)
