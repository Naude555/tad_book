from collections import defaultdict
import uuid
from django.shortcuts import get_object_or_404, redirect, render, HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q
from datetime import date, datetime, timedelta
import calendar
from django.utils.timezone import get_current_timezone_name
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from accounts.models import Asset, BookableAsset, CustomUser, Membership, Organization


import calendar

from accounts.utils.date_time import (
    get_current_time,
    get_date_variables_from_string_date,
    get_formatted_time_now_cal,
)
from accounts.utils.permissions import check_organization_permission
from bookings.forms import (
    AddParticipantForm,
    BookingForm,
    BookingFormAsset,
    BookingFormOrganization,
)
from bookings.models import Bookings
from bookings.services import get_available_slots_for_bookable_asset
from bookings.utils.db_helpers import (
    check_no_bookings_day,
    get_weekday_num_from_date,
    get_is_working_day,
    is_in_bookable_time_frame,
)
from bookings.utils.validation_utils import validate_booking

# Create your views here.


@login_required
def homepage(request, organization_slug):
    organization = get_object_or_404(Organization, slug=organization_slug)
    if request.user not in organization.members.all():
        return redirect("acconuts:organizations")

    assets = (
        Asset.objects.filter(organization=organization)
        .annotate(bookable_assets_count=Count("bookable_assets"))
        .filter(bookable_assets_count__gt=0)
    )

    today = datetime.now()
    formatted_date = today.strftime("%a, %B %d, %Y")
    current_day = today.day
    current_month = today.month
    current_year = today.year
    rows = get_calendar_rows(current_month, current_year)
    month_year = f"{calendar.month_name[current_month]} - {current_year}"
    context = {
        "dayNames": calendar.day_name,
        "rows": rows,
        "currentDay": current_day,
        "currentMonth": current_month,
        "monthYear": month_year,
        "currentYear": current_year,
        "current_date": today,
        "timezone": get_current_timezone_name(),
        "formatted_date": formatted_date,
        "selected_date": today.strftime("%d-%m-%Y"),
        "organization": organization,
        "assets": assets,
    }

    return render(request, "bookings/homepage.html", context)


# views.py


def get_calendar_rows(month, year):
    # Calculate number of days in the month
    _, days_in_month = calendar.monthrange(year, month)

    # Calculate the first day of the month (0 = Monday, 6 = Sunday)
    first_day = calendar.monthrange(year, month)[0]

    # Calculate the number of days in the first week
    first_week_days = 7 - first_day

    # Calculate the number of remaining days
    remaining_days = days_in_month - first_week_days

    # Calculate the number of rows needed (including the first week)
    rows_needed = (remaining_days + 6) // 7 + 1

    # Initialize the calendar with empty rows
    rows = [["" for _ in range(7)] for _ in range(rows_needed)]

    # Populate the first week
    x = 1
    for j in range(first_day, 7):
        rows[0][j] = x
        x += 1

    # Populate the remaining rows
    for i in range(1, rows_needed):
        for j in range(7):
            dt = first_week_days + (i - 1) * 7 + (j + 1)
            if dt <= days_in_month:
                rows[i][j] = dt
            else:
                rows[i][j] = ""

    print(rows)

    return rows


def index(request):
    today = datetime.now()
    current_month = today.month
    current_year = today.year
    rows = get_calendar_rows(current_month, current_year)
    month_year = f"{calendar.month_name[current_month]} - {current_year}"
    return render(
        request,
        "index.html",
        {
            "dayNames": calendar.day_name,
            "rows": rows,
            "currentMonth": current_month,
            "monthYear": month_year,
            "currentYear": current_year,
        },
    )


def next_month(request):
    current_month = int(request.GET.get("currentMonth"))
    current_year = int(request.GET.get("currentYear"))
    current_month += 1
    if current_month > 12:
        current_month = 1
        current_year += 1

    today = datetime.now()
    if today.month == current_month and today.year == current_year:
        current_day = today.day
    elif today.month > current_month or today.year > current_year:
        current_day = (
            40  # Unrealistic date as to force all days to be smaller than current
        )
    else:
        current_day = -1  # unrealistic date to force all date to be larger

    rows = get_calendar_rows(current_month, current_year)
    month_year = f"{calendar.month_name[current_month]} - {current_year}"
    context = {
        "dayNames": calendar.day_name,
        "rows": rows,
        "currentDay": current_day,
        "currentMonth": current_month,
        "monthYear": month_year,
        "currentYear": current_year,
        "current_date": today,
    }

    return render(request, "bookings/partials/full_calendar.html", context)


def previous_month(request):
    current_month = int(request.GET.get("currentMonth"))
    current_year = int(request.GET.get("currentYear"))
    current_month -= 1
    if current_month < 1:
        current_month = 12
        current_year -= 1

    today = datetime.now()
    if today.month == current_month and today.year == current_year:
        current_day = today.day
    elif today.month > current_month or today.year > current_year:
        current_day = (
            40  # Unrealistic date as to force all days to be smaller than current
        )
    else:
        current_day = -1  # unrealistic date to force all date to be larger

    rows = get_calendar_rows(current_month, current_year)
    month_year = f"{calendar.month_name[current_month]} - {current_year}"
    context = {
        "dayNames": calendar.day_name,
        "rows": rows,
        "currentDay": current_day,
        "currentMonth": current_month,
        "monthYear": month_year,
        "currentYear": current_year,
        "current_date": today,
    }

    return render(request, "bookings/partials/full_calendar.html", context)


def today(request):

    today = datetime.now()
    formatted_date = today.strftime("%a, %B %d, %Y")
    current_day = today.day
    current_month = today.month
    current_year = today.year
    rows = get_calendar_rows(current_month, current_year)
    month_year = f"{calendar.month_name[current_month]} - {current_year}"
    selected_date = today.strftime("%d-%m-%Y")
    asset_id = request.GET.get("asset")
    bookable_asset_id = request.GET.get("bookable_asset")
    available_slots = []
    print(selected_date)
    if asset_id and bookable_asset_id:
        available_slots = get_available_slots(
            selected_date, asset_id, bookable_asset_id
        )
        if isinstance(available_slots, HttpResponse):
            available_slots = []

    print(available_slots)
    context = {
        "dayNames": calendar.day_name,
        "rows": rows,
        "currentDay": current_day,
        "currentMonth": current_month,
        "monthYear": month_year,
        "currentYear": current_year,
        "current_date": today,
        "formatted_date": formatted_date,
        "selected_date": selected_date,
        "available_slots": available_slots,
    }

    return render(request, "bookings/partials/full_calendar_today.html", context)


def modal(request):
    # Handle modal logic
    pass


def time_slots(request):
    selected_date = request.GET.get("selected_date")
    asset_id = request.GET.get("asset")
    bookable_asset_id = request.GET.get("bookable_asset")

    date_obj, today_date, formatted_date = get_date_variables_from_string_date(
        selected_date
    )

    if date_obj < today_date:
        return HttpResponse(
            generate_time_slots_html_response(
                selected_date, formatted_date, "Date is in the past."
            )
        )
    available_slots = []
    if date_obj >= today_date:
        if asset_id and bookable_asset_id:
            available_slots = get_available_slots(
                selected_date, asset_id, bookable_asset_id
            )
            if isinstance(available_slots, HttpResponse):
                return available_slots

    context = {
        "formatted_date": formatted_date,
        "selected_date": selected_date,
        "available_slots": available_slots,
    }
    return render(request, "bookings/partials/time_slots.html", context)


def get_available_slots(selected_date, asset_id, bookable_asset_id):
    date_obj, today_date, formatted_date = get_date_variables_from_string_date(
        selected_date
    )

    if check_no_bookings_day(asset_id=asset_id, date=date_obj):
        return HttpResponse(
            generate_time_slots_html_response(
                selected_date, formatted_date, "This day is not available for booking."
            )
        )

    weekday_num = get_weekday_num_from_date(date_obj)
    if not get_is_working_day(asset_id=asset_id, day=weekday_num):
        return HttpResponse(
            generate_time_slots_html_response(
                selected_date,
                formatted_date,
                "This day is not a work day for this booking option.",
            )
        )

    if not is_in_bookable_time_frame(asset_id=asset_id, target_date=date_obj):
        return HttpResponse(
            generate_time_slots_html_response(
                selected_date,
                formatted_date,
                "This day is too far ahead and not available for booking.",
            )
        )

    available_slots = get_available_slots_for_bookable_asset(
        bookable_asset_id, date_obj
    )
    print(available_slots)

    if date_obj == date.today():
        current_time = timezone.localtime().time()
        print(current_time)
        available_slots = [
            slot for slot in available_slots if slot.time() > current_time
        ]

    available_slots = [slot.strftime("%H:%M") for slot in available_slots]

    if not available_slots:
        return HttpResponse(
            generate_time_slots_html_response(
                selected_date, formatted_date, "Fully Booked."
            )
        )

    return available_slots


def generate_time_slots_html_response(selected_date, formatted_date, error_message):
    return f"""
        <div id="time_slots" class="p-4 bg-gray-100 rounded-lg flex-grow">
            <div class="text-lg font-semibold mb-2">
                <input hidden id="selected_date" name="selected_date" value="{selected_date}" />
                {formatted_date}
            </div>
            <div class="bg-white p-4 rounded-lg shadow h-4/5">
                <div class="text-red-600 mb-2"></div>
                <div class="error-message"><p class="text-red-600 mb-2">{error_message}</p></div>
            </div>
        </div>
    """


@login_required
def request_booking(request, time_slot):
    user = request.user
    bookable_asset_id = request.POST.get("bookable_asset")
    selected_date = request.POST.get("selected_date")
    notes = request.POST.get("notes")
    date_obj, today_date, formatted_date = get_date_variables_from_string_date(
        selected_date
    )

    # Get the bookable asset or return a 404 if not found
    bookable_asset = get_object_or_404(BookableAsset, id=bookable_asset_id)
    organization = bookable_asset.asset.organization

    # Check if the user is authorized to make a booking
    if user not in organization.members.all():
        return HttpResponse("User Not authorized Request Made")

    # Parse the time_slot and selected_date
    try:
        start_time = datetime.strptime(time_slot, "%H:%M").time()
    except ValueError:
        return HttpResponse("Invalid time format")

    # Calculate the end time
    slot_duration = timedelta(minutes=bookable_asset.asset.get_slot_duration())
    end_time = (datetime.combine(date_obj, start_time) + slot_duration).time()

    # Create the booking
    booking = Bookings.objects.create(
        user=user,
        date=date_obj,
        start_time=start_time,
        end_time=end_time,
        bookable_asset=bookable_asset,
        notes=notes,
    )

    if booking.status == "accepted":
        print("Send confirmation email")

    success_message = f"A booking has been requested for {formatted_date} at {time_slot}. <br> Current booking status is {booking.status}"
    return HttpResponse(
        f"""
        <div class="bg-green-600 border px-4 py-3 rounded relative mb-4" role="alert">
            <span class="block sm:inline">
                { success_message }
            </span>
        </div>
        <div class="flex items-center justify-between rounded-md  mb-2">
            <button 
                hx-get="/tad_book/bookings/time_slots/" 
                hx-target="#time_slots" 
                hx-include="[name='asset'], [name='selected_date'], [name='bookable_asset']" 
                class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded transition duration-200 ease-in-out transform hover:scale-105"
            >
                Make a new booking
            </button>
            <a href="/tad_book/bookings/{ booking.id }/participants/"
                class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded transition duration-200 ease-in-out transform hover:scale-105 text-center"
            >
                Add participants
            </a>
        </div>

    """
    )


@login_required
def booking_participants(request, booking_id):
    booking = get_object_or_404(Bookings, id=booking_id)
    participants = booking.participants.all()
    print(participants)
    context = {"booking": booking, "participants": participants}
    return render(request, "bookings/booking_participants.html", context)


@login_required
def booking_participant_add(request, booking_id):
    booking = get_object_or_404(Bookings, id=booking_id)
    participants = booking.participants.all()

    if request.method == "POST":
        form = AddParticipantForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            user = CustomUser.objects.filter(email=email).first()
            if user:
                booking.participants.add(user)
            else:
                # Generate an invitation token for the new user
                token = str(uuid.uuid4())

                # Create a new user and set is_active to False
                user = CustomUser.objects.create(
                    username=token,
                    email=email,
                    is_active=False,
                )
                booking.participants.add(user)

            return render(
                request,
                "bookings/partials/participant.html",
                {"booking": booking, "participant": user},
            )
    else:
        form = AddParticipantForm()

    context = {"booking": booking, "participants": participants, "form": form}
    return render(request, "bookings/partials/participant_create_form.html", context)


@login_required
def booking_participant_remove(request, booking_id, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    booking = get_object_or_404(Bookings, id=booking_id)
    try:
        booking.remove_participant(user)
        return HttpResponse(
            f"Email {user.email} was removed from the partisipants list."
        )
    except ValueError as e:
        print(e)


# TODO: Check this


def events(request):
    # Handle events logic
    pass


@login_required
def get_bookable_assets(request):
    asset_id = request.GET.get("asset")
    asset = get_object_or_404(Asset, id=asset_id)
    user_admin = asset.organization.members.filter(
        id=request.user.id, membership__role="admin"
    ).exists()
    if asset.admin_assigns_booking and not user_admin:
        bookable_assets = BookableAsset.objects.filter(asset=asset).filter(name="Any")
    else:
        bookable_assets = BookableAsset.objects.filter(asset=asset)
    context = {"asset": asset, "bookable_assets": bookable_assets}
    return render(
        request,
        "bookings/partials/booking_details_bookable_asset_dropdown.html",
        context,
    )


@login_required
def manage_bookings_admin_calendar_view(request, user_slug):
    # Filter organizations where the user is an admin
    admin_memberships = Membership.objects.filter(user__slug=user_slug, role="admin")
    admin_organizations = Organization.objects.filter(membership__in=admin_memberships)

    # Use select_related to optimize the query
    bookings = Bookings.objects.select_related(
        "user", "bookable_asset__asset__organization"
    ).filter(bookable_asset__asset__organization__in=admin_organizations)
    events = []

    for booking in bookings:
        events.append(
            {
                "title": f"{booking.user.username}",
                "start": f"{booking.date}T{booking.start_time}",
                "end": f"{booking.date}T{booking.end_time}",
                "url": f"/tad_book/bookings/manage_bookings/admin/{booking.id}/edit/form/",
                "color": (
                    booking.bookable_asset.calendar_colour
                    if booking.status == "accepted"
                    else "red"
                ),
            }
        )
    participant_bookings = Bookings.objects.filter(
        participants=request.user,
    ).exclude(user=request.user)

    for booking in participant_bookings:
        events.append(
            {
                "title": f"{booking.user.username}",
                "start": f"{booking.date}T{booking.start_time}",
                "end": f"{booking.date}T{booking.end_time}",
                "url": f"/tad_book/bookings/manage_bookings/view/{booking.id}/",
                "color": "gray",
            }
        )

    context = {
        "events": events,
    }

    return render(request, "bookings/manage_bookings_admin_calendar_view.html", context)


def manage_bookings_admin_upcoming_list_view(request, user_slug):
    admin_memberships = Membership.objects.filter(user__slug=user_slug, role="admin")
    admin_organizations = Organization.objects.filter(membership__in=admin_memberships)

    # Use select_related to optimize the query
    bookings = (
        Bookings.objects.select_related("user", "bookable_asset__asset__organization")
        .filter(bookable_asset__asset__organization__in=admin_organizations)
        .filter(
            Q(date=date.today(), end_time__gte=get_current_time())
            | Q(date__gt=date.today())
        )
    )

    # Using defaultdict and comprehensions for efficiency
    grouped_data = defaultdict(list)
    for booking in bookings:
        grouped_data[booking.bookable_asset.asset.organization].append(booking)

    # Convert defaultdict to regular dict for easier debugging in template
    grouped_data = dict(grouped_data)

    context = {
        "grouped_data": grouped_data,
    }
    return render(
        request, "bookings/manage_bookings_admin_upcoming_list_view.html", context
    )


@login_required
def manage_booking_admin_edit(request, booking_id):
    booking = get_object_or_404(Bookings, id=booking_id)
    print(booking.id)

    if request.method == "POST":
        print("in the post")
        form = BookingFormOrganization(
            request.POST,
            asset=booking.bookable_asset.asset,
            instance=booking,
        )
        if form.is_valid():

            # Perform validation checks
            has_error = validate_booking(booking, form)

            # Only save the booking if no errors were found
            if not has_error:
                form.save()
                context = {"booking": booking}
                return render(request, "bookings/partials/booking_admin.html", context)
    else:
        form = BookingFormOrganization(
            asset=booking.bookable_asset.asset, instance=booking
        )

    context = {"form": form, "booking": booking}
    return render(request, "bookings/partials/booking_admin_edit.html", context)


@login_required
def manage_booking_admin_edit_form(request, booking_id):
    booking = get_object_or_404(Bookings, id=booking_id)
    organization = booking.bookable_asset.asset.organization
    permission_response = check_organization_permission(request, organization)
    if permission_response:
        return permission_response

    if request.method == "POST":
        print("in the post")
        form = BookingFormOrganization(
            request.POST,
            asset=booking.bookable_asset.asset,
            instance=booking,
        )
        if form.is_valid():

            # Perform validation checks
            has_error = validate_booking(booking, form)

            if not has_error:
                form.save()
                context = {"booking": booking}

                return redirect(
                    "bookings:manage_bookings_admin_calendar_view",
                    user_slug=request.user.slug,
                )

    else:
        form = BookingFormOrganization(
            asset=booking.bookable_asset.asset, instance=booking
        )
    participants = booking.participants.all()

    context = {
        "form": form,
        "booking": booking,
        "participants": participants,
        "admin_view": True,
    }
    return render(request, "bookings/booking_admin_edit_form.html", context)


@login_required
def manage_booking_admin_get(request, booking_id):
    booking = get_object_or_404(Bookings, id=booking_id)

    context = {"booking": booking}
    return render(request, "bookings/partials/booking_admin.html", context)


@login_required
def manage_bookings_organization_calendar_view(request, organization_slug):
    organization = get_object_or_404(Organization, slug=organization_slug)

    bookings = Bookings.objects.select_related(
        "user", "bookable_asset__asset__organization"
    ).filter(bookable_asset__asset__organization=organization)

    events = []

    for booking in bookings:
        events.append(
            {
                "title": f"{booking.user.username}",
                "start": f"{booking.date}T{booking.start_time}",
                "end": f"{booking.date}T{booking.end_time}",
                "url": f"/tad_book/bookings/manage_bookings/organization/{booking.id}/edit/form/",
                "color": (
                    booking.bookable_asset.calendar_colour
                    if booking.status == "accepted"
                    else "red"
                ),
            }
        )

    context = {"events": events, "organization": organization}

    return render(
        request, "bookings/manage_bookings_organization_calendar_view.html", context
    )


def manage_bookings_organization_upcoming_list_view(request, organization_slug):
    organization = get_object_or_404(Organization, slug=organization_slug)

    bookings = (
        Bookings.objects.select_related("user", "bookable_asset__asset__organization")
        .filter(bookable_asset__asset__organization=organization)
        .filter(
            Q(date=date.today(), end_time__gte=get_current_time())
            | Q(date__gt=date.today())
        )
    )

    # Using defaultdict and comprehensions for efficiency
    grouped_data = defaultdict(list)
    for booking in bookings:
        grouped_data[booking.bookable_asset.asset].append(booking)

    # Convert defaultdict to regular dict for easier debugging in template
    grouped_data = dict(grouped_data)

    context = {
        "organization": organization,
        "grouped_data": grouped_data,
    }

    return render(
        request,
        "bookings/manage_bookings_organization_upcoming_list_view.html",
        context,
    )


@login_required
def manage_booking_organization_edit_form(request, booking_id):
    booking = get_object_or_404(Bookings, id=booking_id)
    organization = booking.bookable_asset.asset.organization
    permission_response = check_organization_permission(request, organization)
    if permission_response:
        return permission_response

    if request.method == "POST":
        print("in the post")
        form = BookingFormOrganization(
            request.POST,
            asset=booking.bookable_asset.asset,
            instance=booking,
        )
        if form.is_valid():
            print("form valid")

            # Perform validation checks
            has_error = validate_booking(booking, form)
            print(f"Has error : {has_error}")
            # Only save the booking if no errors were found
            if not has_error:

                instance = form.save(False)
                print(f"########### {instance.status} #######")
                instance.save()
                context = {"booking": booking}
                return redirect(
                    "bookings:manage_bookings_organization_calendar_view",
                    organization_slug=organization.slug,
                )
        else:
            print(form.errors)
    else:
        form = BookingFormOrganization(
            asset=booking.bookable_asset.asset, instance=booking
        )
    participants = booking.participants.all()

    context = {
        "form": form,
        "booking": booking,
        "participants": participants,
        "admin_view": True,
    }
    return render(request, "bookings/booking_admin_edit_form.html", context)


@login_required
def manage_booking_organization_edit(request, booking_id):
    booking = get_object_or_404(Bookings, id=booking_id)
    print(booking.id)

    if request.method == "POST":
        print("in the post")
        form = BookingFormOrganization(
            request.POST,
            asset=booking.bookable_asset.asset,
            instance=booking,
        )
        if form.is_valid():

            # Perform validation checks
            has_error = validate_booking(booking, form)

            # Only save the booking if no errors were found
            if not has_error:
                form.save()
                context = {"booking": booking}
                return render(
                    request, "bookings/partials/booking_organization.html", context
                )
    else:
        form = BookingFormOrganization(
            asset=booking.bookable_asset.asset, instance=booking
        )

    context = {"form": form, "booking": booking}
    return render(request, "bookings/partials/booking_organization_edit.html", context)


@login_required
def manage_booking_organization_get(request, booking_id):
    booking = get_object_or_404(Bookings, id=booking_id)

    context = {"booking": booking}
    return render(request, "bookings/partials/booking_organization.html", context)


@login_required
def manage_bookings_asset_calendar_view(request, asset_slug):
    asset = get_object_or_404(Asset, slug=asset_slug)

    bookings = Bookings.objects.select_related(
        "user", "bookable_asset__asset__organization"
    ).filter(bookable_asset__asset=asset)

    events = []

    for booking in bookings:
        events.append(
            {
                "title": f"{booking.user.username}",
                "start": f"{booking.date}T{booking.start_time}",
                "end": f"{booking.date}T{booking.end_time}",
                "url": f"/tad_book/bookings/manage_bookings/organization/{booking.id}/edit/form/",
                "color": (
                    booking.bookable_asset.calendar_colour
                    if booking.status == "accepted"
                    else "red"
                ),
            }
        )

    context = {"events": events, "asset": asset}

    return render(request, "bookings/manage_bookings_asset_calendar_view.html", context)


@login_required
def manage_bookings_asset_upcoming_list_view(request, asset_slug):
    asset = get_object_or_404(Asset, slug=asset_slug)

    bookings = (
        Bookings.objects.select_related("user", "bookable_asset__asset__organization")
        .filter(bookable_asset__asset=asset)
        .filter(
            Q(date=date.today(), end_time__gte=get_current_time())
            | Q(date__gt=date.today())
        )
    )

    # Using defaultdict and comprehensions for efficiency
    grouped_data = defaultdict(list)
    for booking in bookings:
        grouped_data[booking.bookable_asset].append(booking)

    # Convert defaultdict to regular dict for easier debugging in template
    grouped_data = dict(grouped_data)

    context = {
        "asset": asset,
        "grouped_data": grouped_data,
    }

    return render(
        request, "bookings/manage_bookings_assets_upcoming_list_view.html", context
    )


@login_required
def manage_bookings_bookable_asset_calendar_view(request, bookable_asset_slug):
    bookable_asset = get_object_or_404(BookableAsset, slug=bookable_asset_slug)

    bookings = Bookings.objects.select_related("user").filter(
        bookable_asset=bookable_asset
    )

    events = []

    for booking in bookings:
        events.append(
            {
                "title": f"{booking.user.username}",
                "start": f"{booking.date}T{booking.start_time}",
                "end": f"{booking.date}T{booking.end_time}",
                "url": f"/tad_book/bookings/manage_bookings/organization/{booking.id}/edit/form/",
                "color": (
                    booking.bookable_asset.calendar_colour
                    if booking.status == "accepted"
                    else "red"
                ),
            }
        )

    context = {
        "events": events,
        "bookable_asset": bookable_asset,
        "now": get_formatted_time_now_cal(),
    }
    print(context)

    return render(
        request, "bookings/manage_bookings_bookable_asset_calendar_view.html", context
    )


def manage_bookings_bookable_asset_calendar_view_share_link(
    request, bookable_asset_slug
):
    bookable_asset = get_object_or_404(BookableAsset, slug=bookable_asset_slug)
    if bookable_asset.share_link:
        bookings = Bookings.objects.select_related("user").filter(
            bookable_asset=bookable_asset
        )

        events = []

        for booking in bookings:
            events.append(
                {
                    "title": f"{booking.user.username}",
                    "start": f"{booking.date}T{booking.start_time}",
                    "end": f"{booking.date}T{booking.end_time}",
                    "url": f"/tad_book/bookings/manage_bookings/view/{booking.id}/share_link/",
                    "color": (
                        booking.bookable_asset.calendar_colour
                        if booking.status == "accepted"
                        else "red"
                    ),
                }
            )

        context = {
            "events": events,
            "bookable_asset": bookable_asset,
            "now": get_formatted_time_now_cal(),
        }
        print(context)

        return render(
            request,
            "bookings/manage_bookings_bookable_asset_calendar_view_share_link.html",
            context,
        )
    else:
        return HttpResponse("Share link not available.")


def manage_bookings_organization_upcoming_list_view(request, organization_slug):
    organization = get_object_or_404(Organization, slug=organization_slug)

    bookings = (
        Bookings.objects.select_related("user", "bookable_asset__asset__organization")
        .filter(bookable_asset__asset__organization=organization)
        .filter(
            Q(date=date.today(), end_time__gte=get_current_time())
            | Q(date__gt=date.today())
        )
    )

    # Using defaultdict and comprehensions for efficiency
    grouped_data = defaultdict(list)
    for booking in bookings:
        grouped_data[booking.bookable_asset.asset].append(booking)

    # Convert defaultdict to regular dict for easier debugging in template
    grouped_data = dict(grouped_data)

    context = {
        "organization": organization,
        "grouped_data": grouped_data,
    }

    return render(
        request,
        "bookings/manage_bookings_organization_upcoming_list_view.html",
        context,
    )


@login_required
def manage_booking_asset_edit(request, booking_id):
    booking = get_object_or_404(Bookings, id=booking_id)
    print(booking.id)

    if request.method == "POST":
        print("in the post")
        form = BookingFormAsset(request.POST, instance=booking)
        if form.is_valid():

            # Perform validation checks
            has_error = validate_booking(booking, form)

            # Only save the booking if no errors were found
            if not has_error:
                form.save()
                context = {"booking": booking}
                return render(request, "bookings/partials/booking_asset.html", context)
    else:
        form = BookingFormAsset(instance=booking)

    context = {"form": form, "booking": booking}
    return render(request, "bookings/partials/booking_asset_edit.html", context)


@login_required
def manage_booking_asset_get(request, booking_id):
    booking = get_object_or_404(Bookings, id=booking_id)

    context = {"booking": booking}
    return render(request, "bookings/partials/booking_asset.html", context)


@login_required
def manage_bookings_bookable_asset(request, bookable_asset_slug):
    return HttpResponse("Manage bookings bookable_asset")


@login_required
def manage_bookings_user_calendar_view(request, user_slug):
    """
    Profile landing page view.
    """
    user_slug = request.user.slug
    # Filter organizations where the user is member or admin
    memberships = Membership.objects.filter(user__slug=user_slug)

    admin_memberships = memberships.filter(role=Membership.ADMIN)
    admin_organizations = Organization.objects.filter(membership__in=admin_memberships)

    # Use select_related to optimize the query
    admin_bookings = (
        Bookings.objects.select_related("user", "bookable_asset__asset__organization")
        .filter(bookable_asset__asset__organization__in=admin_organizations)
        .exclude(status__in=["rejected", "canceled"])
    )
    events = []

    for booking in admin_bookings:
        events.append(
            {
                "title": (
                    f"{booking.bookable_asset.name}: {booking.user.username} - ({booking.notes})"
                    if booking.notes
                    else f"{booking.bookable_asset.name}: {booking.user.username}"
                ),
                "start": f"{booking.date}T{booking.start_time}",
                "end": f"{booking.date}T{booking.end_time}",
                "url": f"/tad_book/bookings/manage_bookings/admin/{booking.id}/edit/form/",
                "textColor": "White",
                "color": (
                    booking.bookable_asset.calendar_colour
                    if booking.status == "accepted"
                    else "red"
                ),
            }
        )

    # Filter organizations where the user is a member
    member_memberships = (
        Bookings.objects.select_related("user", "bookable_asset__asset__organization")
        .filter(user=request.user)
        .exclude(bookable_asset__asset__organization__in=admin_organizations)
        .exclude(status__in=["rejected", "canceled"])
    )

    for booking in member_memberships:
        events.append(
            {
                "title": (
                    f"{booking.bookable_asset.asset} - ({booking.notes})"
                    if booking.notes
                    else f"{booking.bookable_asset.asset}"
                ),
                "start": f"{booking.date}T{booking.start_time}",
                "end": f"{booking.date}T{booking.end_time}",
                "url": f"/tad_book/bookings/manage_bookings/view/{booking.id}/",
                "textColor": "black",
                "color": ("green" if booking.status == "accepted" else "yellow"),
            }
        )

    participant_bookings = (
        Bookings.objects.filter(
            participants=request.user,
        )
        .exclude(user=request.user)
        .exclude(status__in=["rejected", "canceled"])
    )

    for booking in participant_bookings:
        events.append(
            {
                "title": f"Participant of {booking.bookable_asset.asset.name} - {booking.bookable_asset.name}",
                "start": f"{booking.date}T{booking.start_time}",
                "end": f"{booking.date}T{booking.end_time}",
                "url": f"/tad_book/bookings/manage_bookings/view/{booking.id}/",
                "textColor": "black" if booking.status == "accepted" else "yellow",
                "color": "gray",
            }
        )

    context = {
        "events": events,
    }

    return render(request, "bookings/manage_bookings_user_calendar_view.html", context)


@login_required
def manage_bookings_user_upcoming_list_view(request, user_slug):
    # Filter organizations where the user is an admin
    memberships = Membership.objects.filter(user__slug=user_slug)
    organizations = Organization.objects.filter(membership__in=memberships)

    bookings = (
        Bookings.objects.select_related("user", "bookable_asset__asset__organization")
        .filter(bookable_asset__asset__organization__in=organizations)
        .filter(
            Q(date=date.today(), end_time__gte=get_current_time())
            | Q(date__gt=date.today())
        )
        .filter(user__slug=user_slug)
    )

    # Using defaultdict and comprehensions for efficiency
    grouped_data = defaultdict(list)
    for booking in bookings:
        grouped_data[booking.bookable_asset.asset.organization].append(booking)

    # Convert defaultdict to regular dict for easier debugging in template
    grouped_data = dict(grouped_data)

    context = {
        "grouped_data": grouped_data,
    }

    return render(request, "bookings/manage_bookings_user_list_view.html", context)


@login_required
def manage_booking_user_cancel(request, booking_id):
    booking = get_object_or_404(Bookings, id=booking_id)
    if request.user != booking.user:
        return HttpResponse("Not your booking")

    if request.method == "POST":
        booking.status = "canceled"
        booking.save()
        context = {"booking": booking}
        return render(request, "bookings/partials/booking_user.html", context)


@login_required
def manage_booking_user_get(request, booking_id):
    booking = get_object_or_404(Bookings, id=booking_id)

    context = {"booking": booking}
    return render(request, "bookings/partials/booking_user.html", context)


@login_required
def custom_booking(request, asset_slug):
    asset = get_object_or_404(Asset, slug=asset_slug)
    bookable_asset_id = request.GET.get("bookable_asset")

    if bookable_asset_id:
        try:
            bookable_asset = BookableAsset.objects.get(
                id=bookable_asset_id, asset=asset
            )
        except BookableAsset.DoesNotExist:
            bookable_asset = None
    else:
        bookable_asset = None

    if request.method == "POST":
        form = BookingForm(request.POST, asset=asset, bookable_asset=bookable_asset)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.user = request.user

            # Perform validation checks
            has_error = validate_booking(booking, form)

            # Only save the booking if no errors were found
            if not has_error:
                booking.save()
                return redirect(
                    "bookings:manage_bookings_asset_upcoming_list_view",
                    asset_slug=asset.slug,
                )
    else:
        form = BookingForm(asset=asset, bookable_asset=bookable_asset)

    return render(
        request, "bookings/custom_booking_form.html", {"form": form, "asset": asset}
    )


@login_required
def get_today_bookings(request):
    user = request.user
    admin = request.POST.get("admin")

    memberships = Membership.objects.filter(user=user)
    if admin:
        memberships = memberships.filter(role="admin")

    organizations = Organization.objects.filter(membership__in=memberships)

    bookings = Bookings.objects.select_related(
        "user", "bookable_asset__asset__organization"
    ).filter(
        bookable_asset__asset__organization__in=organizations,
        date=date.today(),
        end_time__gte=get_current_time(),
        user=user,
    )

    grouped_data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    for booking in bookings:
        organization = booking.bookable_asset.asset.organization
        asset = booking.bookable_asset.asset
        bookable_asset = booking.bookable_asset
        grouped_data[organization][asset][bookable_asset].append(booking)

    # Convert defaultdict to a regular dictionary
    def convert_to_regular_dict(d):
        if isinstance(d, defaultdict):
            d = {k: convert_to_regular_dict(v) for k, v in d.items()}
        return d

    grouped_data = convert_to_regular_dict(grouped_data)

    context = {
        "grouped_data": grouped_data,
    }

    return render(request, "bookings/partials/bookings_today.html", context)


@login_required
def get_today_bookings_participants(request):
    bookings = Bookings.objects.filter(
        date=date.today(),
        participants=request.user,
        end_time__gte=get_current_time(),
        # id=3
    )
    # bookings = Bookings.objects.all()
    print("participants")
    print(bookings)
    grouped_data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    for booking in bookings:
        organization = booking.bookable_asset.asset.organization
        asset = booking.bookable_asset.asset
        bookable_asset = booking.bookable_asset
        grouped_data[organization][asset][bookable_asset].append(booking)

    # Convert defaultdict to a regular dictionary
    def convert_to_regular_dict(d):
        if isinstance(d, defaultdict):
            d = {k: convert_to_regular_dict(v) for k, v in d.items()}
        return d

    grouped_data = convert_to_regular_dict(grouped_data)
    print(grouped_data)  # Debug print statement

    context = {
        "grouped_data": grouped_data,
    }

    return render(
        request, "bookings/partials/bookings_today_participants.html", context
    )


@login_required
def approve_booking(request, booking_id, token):
    booking = get_object_or_404(Bookings, id=booking_id)
    permission_response = check_organization_permission(
        request, booking.bookable_asset.asset.organization
    )
    if permission_response:
        return permission_response

    # Verify the token
    if booking.token == token:
        booking.status = "accepted"
        booking.save()
        return redirect(
            "bookings:manage_booking_admin_edit_form", booking_id=booking.id
        )
    else:
        return HttpResponse("Invalid approval link.")


@login_required
def reject_booking(request, booking_id, token):
    print("in the reject booking")
    booking = get_object_or_404(Bookings, id=booking_id)
    permission_response = check_organization_permission(
        request, booking.bookable_asset.asset.organization
    )
    if permission_response:
        return permission_response

    # Verify the token
    if booking.token == token:
        booking.status = "rejected"
        booking.save()
        return redirect(
            "bookings:manage_booking_admin_edit_form", booking_id=booking.id
        )
    else:
        return HttpResponse("Invalid reject link.")


@login_required
def cancel_booking(request, booking_id, token):
    booking = get_object_or_404(Bookings, id=booking_id)
    permission_response = check_organization_permission(
        request,
        booking.bookable_asset.asset.organization,
        required_role=Membership.MEMBER,
    )
    if permission_response:
        return permission_response

    # Verify the token
    if booking.token == token:
        booking.status = "canceled"
        booking.save()
        return redirect("bookings:manage_booking_view", booking_id=booking.id)
    else:
        return HttpResponse("Invalid cancel link.")


@login_required
def manage_booking_view(request, booking_id):
    booking = get_object_or_404(Bookings, id=booking_id)
    participants = booking.participants.all()

    context = {"booking": booking, "participants": participants}
    return render(request, "bookings/manage_booking_view.html", context)


def manage_booking_view_share_link(request, booking_id):
    print("in the share link")
    booking = get_object_or_404(Bookings, id=booking_id)
    if booking.bookable_asset.share_link:
        context = {"booking": booking}
        return render(request, "bookings/manage_booking_view_share_link.html", context)
    else:
        return HttpResponse("Share link not available.")


def test(request):
    bookings = Bookings.objects.select_related(
        "bookable_asset__asset__organization"
    ).all()
    events = []

    for booking in bookings:
        organization = booking.bookable_asset.asset.organization
        events.append(
            {
                "title": f"Booking by {booking.user.username}",
                "start": f"{booking.date}T{booking.start_time}",
                "end": f"{booking.date}T{booking.end_time}",
                "url": f"/manage_bookings/admin/{booking.id}/edit/",
                "color": booking.bookable_asset.asset.calendar_colour,  # Assuming Organization model has a color field
            }
        )

    context = {
        "events": events,
    }
    return render(request, "bookings/test.html", context)


def upcomming_bookings_count(request, organization_id):
    organization = get_object_or_404(Organization, id=organization_id)
    bookings = Bookings.objects.filter(
        bookable_asset__asset__organization=organization,
        date__gte=date.today(),
        start_time__gte=get_current_time(),
        status="accepted",
    )
    count = bookings.count()
    return HttpResponse(count)


def today_upcomming_bookings_count(request, organization_id):
    organization = get_object_or_404(Organization, id=organization_id)
    bookings = Bookings.objects.filter(
        bookable_asset__asset__organization=organization,
        date__gte=date.today(),
        start_time__gte=get_current_time(),
        status="accepted",
    )
    count = bookings.count()
    return HttpResponse(count)


def current_bookings_count(request, organization_id):
    organization = get_object_or_404(Organization, id=organization_id)
    bookings = Bookings.objects.filter(
        bookable_asset__asset__organization=organization,
        date__gte=date.today(),
        start_time__lte=get_current_time(),
        end_time__gte=get_current_time(),
        status="accepted",
    )
    count = bookings.count()
    return HttpResponse(count)


def upcomming_pending_bookings_count(request, organization_id):
    organization = get_object_or_404(Organization, id=organization_id)
    bookings = Bookings.objects.filter(
        bookable_asset__asset__organization=organization,
        date__gte=date.today(),
        start_time__gte=get_current_time(),
        status="pending",
    )
    count = bookings.count()
    return HttpResponse(count)
