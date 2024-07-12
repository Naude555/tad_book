from datetime import date
import uuid
from django.contrib.auth.views import LoginView
from django.contrib.auth import authenticate, login
from django.forms import ValidationError
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import FormView, TemplateView
from django.contrib.auth import get_user_model
from django.http.response import HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from accounts.models import (
    Asset,
    AssetBookableHours,
    BookableAsset,
    CustomUser,
    Membership,
    Organization,
)
from accounts.utils.date_time import get_formatted_time_now_cal
from accounts.utils.permissions import check_organization_permission
from accounts.utils.seeding import seed_bookable_hours, seed_any_bookable_asset
from bookings.forms import NoBookingsForm
from bookings.models import Bookings, NoBookings
from bookings.utils.booking_utils import cancel_bookings, reject_bookings
from django.db.models import Q


from .forms import (
    AdminManagementForm,
    AssetBookableHoursForm,
    AssetForm,
    BookableAssetForm,
    CustomUserChangeForm,
    InviteMemberForm,
    MembershipForm,
    OrganizationForm,
    RegisterForm,
    RequestAccessForm,
    SetPasswordForm,
)


# Create your views here.
class IndexView(TemplateView):
    """
    A view to render the index page.
    """

    template_name = "index.html"


class Login(LoginView):
    """
    A view to handle user login.
    """

    template_name = "registration/login.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["next"] = self.request.GET.get("next", "")
        return context

    def get_success_url(self):
        print(self.request.POST)
        print(self.request.GET)
        next_url = self.request.POST.get("next", self.request.GET.get("next"))
        print(next_url)
        if next_url:
            return next_url
        return reverse_lazy(
            "accounts:profile"
        )  # Default redirect if 'next' is not provided


class RegisterView(FormView):
    """
    A view to handle user registration.
    """

    form_class = RegisterForm
    template_name = "registration/register.html"
    success_url = reverse_lazy(
        "accounts:profile"
    )  # Change to the desired URL after login

    def form_valid(self, form):
        """
        Handle form submission and user registration.
        """
        user = form.save()  # Save the user
        username = form.cleaned_data.get("username")
        password = form.cleaned_data.get("password1")
        user = authenticate(username=username, password=password)
        if user is not None:
            login(self.request, user)
        return HttpResponseRedirect(self.get_success_url())


def check_username(request):
    """
    Check if a username is already in use.
    """
    print("hello")
    username = request.POST.get("username")
    if len(username) == 0:
        return HttpResponse(
            "<div id='username-error' class='block text-sm font-medium text-red-700'>Username can not be empty</div>"
        )

    if get_user_model().objects.filter(username=username).exists():
        return HttpResponse(
            "<div id='username-error' class='block text-sm font-medium text-red-700'>This username already exists</div>"
        )
    else:
        return HttpResponse(
            "<div id='username-error' class='block text-sm font-medium text-green-700'>This username is available</div>"
        )


def check_username_invitation_token(request, user_slug):
    """
    Check if a username is already in use.
    """
    print("hello")
    username = request.POST.get("username")
    if len(username) == 0:
        return HttpResponse(
            "<div id='username-error' class='block text-sm font-medium text-red-700'>Username Can not be empty</div>"
        )

    account = (
        CustomUser.objects.filter(username=username).exclude(slug=user_slug).first()
    )
    if account:
        return HttpResponse(
            "<div id='username-error' class='block text-sm font-medium text-red-700'>This username already exists</div>"
        )
    else:
        return HttpResponse(
            "<div id='username-error' class='block text-sm font-medium text-green-700'>This username is available</div>"
        )


@login_required
def profile_view(request):
    """
    Profile landing page view.
    """
    user_slug = request.user.slug
    # Filter organizations where the user is member or admin
    memberships = Membership.objects.filter(user__slug=user_slug)

    admin_memberships = memberships.filter(role=Membership.ADMIN)
    admin_organizations = Organization.objects.filter(membership__in=admin_memberships)

    member_memberships = memberships.filter(role=Membership.MEMBER)

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
    print(timezone.now())

    context = {
        "events": events,
        "now": get_formatted_time_now_cal(),
    }

    return render(request, "accounts/profile.html", context)


@login_required
def membership_tables(request):
    user = request.user
    memberships = Membership.objects.filter(user=user)

    organization_ids = memberships.values("organization_id")
    accepted_membership_ids = memberships.filter(status="accepted").values(
        "organization_id"
    )
    invited_membership_ids = memberships.filter(status="invited").values(
        "organization_id"
    )
    pending_membership_ids = memberships.filter(status="pending").values(
        "organization_id"
    )

    organizations = Organization.objects.filter(
        Q(id__in=organization_ids)
        | Q(id__in=accepted_membership_ids)
        | Q(id__in=invited_membership_ids)
        | Q(id__in=pending_membership_ids)
    )

    accepted_membership = organizations.filter(id__in=accepted_membership_ids)
    invited_membership = organizations.filter(id__in=invited_membership_ids)
    pending_membership = organizations.filter(id__in=pending_membership_ids)
    context = {
        "accepted_membership": accepted_membership,
        "invited_membership": invited_membership,
        "pending_membership": pending_membership,
    }
    return render(
        request,
        "accounts/partials/organization_membership_details_tables.html",
        context,
    )


@login_required
def profile_update_view(request):
    try:
        profile = request.user
    except CustomUser.DoesNotExist:
        profile = CustomUser(user=request.user)

    if request.method == "POST":
        form = CustomUserChangeForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect("accounts:profile")
    else:
        form = CustomUserChangeForm(instance=profile)

    return render(request, "accounts/profile_update.html", {"form": form})


@login_required
def organization_views(request):
    user = request.user

    memberships = Membership.objects.filter(user=user)

    admin_memberships = memberships.filter(role=Membership.ADMIN)

    member_memberships = memberships.filter(role=Membership.MEMBER)

    organization_ids = admin_memberships.values("organization_id")
    accepted_membership_ids = member_memberships.filter(status="accepted").values(
        "organization_id"
    )
    invited_membership_ids = member_memberships.filter(status="invited").values(
        "organization_id"
    )
    pending_membership_ids = member_memberships.filter(status="pending").values(
        "organization_id"
    )

    organizations = Organization.objects.filter(
        Q(id__in=organization_ids)
        | Q(id__in=accepted_membership_ids)
        | Q(id__in=invited_membership_ids)
        | Q(id__in=pending_membership_ids)
    )

    admin_organizations = organizations.filter(id__in=organization_ids)
    accepted_membership = organizations.filter(id__in=accepted_membership_ids)
    invited_membership = organizations.filter(id__in=invited_membership_ids)
    pending_membership = organizations.filter(id__in=pending_membership_ids)

    return render(
        request,
        "accounts/organization.html",
        {
            "admin_organizations": admin_organizations,
            "accepted_membership": accepted_membership,
            "invited_membership": invited_membership,
            "pending_membership": pending_membership,
        },
    )


def get_admin_organizations(request):
    user = request.user

    memberships = Membership.objects.filter(user=user)

    admin_memberships = memberships.filter(role=Membership.ADMIN)

    admin_organizations = Organization.objects.filter(
        id__in=admin_memberships.values("organization_id")
    )

    return render(
        request,
        "accounts/partials/organization_table_admin.html",
        {
            "admin_organizations": admin_organizations,
        },
    )


def get_all_membership(request):
    user = request.user

    memberships = Membership.objects.filter(user=user)

    member_memberships = memberships

    accepted_membership = member_memberships.filter(status="accepted")

    accepted_membership = Organization.objects.filter(
        id__in=accepted_membership.values("organization_id")
    )

    return render(
        request,
        "accounts/partials/organization_table_all_member.html",
        {
            "accepted_membership": accepted_membership,
        },
    )


def get_accepted_membership(request):
    user = request.user

    memberships = Membership.objects.filter(user=user)

    member_memberships = memberships.filter(role=Membership.MEMBER)

    accepted_membership = member_memberships.filter(status="accepted")

    accepted_membership = Organization.objects.filter(
        id__in=accepted_membership.values("organization_id")
    )

    return render(
        request,
        "accounts/partials/organization_table_member.html",
        {
            "accepted_membership": accepted_membership,
        },
    )


def get_invited_membership(request):
    user = request.user

    memberships = Membership.objects.filter(user=user)

    member_memberships = memberships.filter(role=Membership.MEMBER)

    invited_membership = member_memberships.filter(status="invited")

    invited_membership = Organization.objects.filter(
        id__in=invited_membership.values("organization_id")
    )

    return render(
        request,
        "accounts/partials/organization_table_invited_member.html",
        {
            "invited_membership": invited_membership,
        },
    )


def get_pending_membership(request):
    user = request.user

    memberships = Membership.objects.filter(user=user)

    member_memberships = memberships.filter(role=Membership.MEMBER)

    pending_membership = member_memberships.filter(status="pending")

    pending_membership = Organization.objects.filter(
        id__in=pending_membership.values("organization_id")
    )

    return render(
        request,
        "accounts/organization_table_join_request.html",
        {
            "pending_membership": pending_membership,
        },
    )


@login_required
def organization_search(request):
    user = request.user

    memberships = Membership.objects.filter(user=user)

    if request.POST:
        pass

    organizations_not_a_member_of = Organization.objects.exclude(
        id__in=memberships.values("organization_id")
    )

    return render(
        request,
        "accounts/organization_search.html",
        {"organizations_not_a_member_of": organizations_not_a_member_of},
    )


@login_required
def create_organization(request):
    if not request.user.can_start_own_organizations:
        return HttpResponse("You cant start your own organization")
    if request.method == "POST":
        form = OrganizationForm(request.POST)
        if form.is_valid():
            # Save the organization instance
            organization = form.save()

            # Create a membership instance for the user, adding them to the organization
            Membership.objects.create(
                user=request.user,
                organization=organization,
                role="admin",  # Set the role to admin
                is_approved=True,  # Mark the membership as approved
                status="accepted",  # Mark the status as accepted
            )

            # Redirect to the organization detail page
            return redirect("accounts:organization_detail", organization.slug)
    else:
        form = OrganizationForm()

    # Render the organization creation form
    return render(request, "accounts/organization_create.html", {"form": form})


@login_required
def asset_create(request, organization_slug):
    organization = get_object_or_404(Organization, slug=organization_slug)

    if request.method == "POST":
        form = AssetForm(request.POST)
        if form.is_valid():
            print("valid")
            asset = form.save(commit=False)
            asset.organization = organization
            asset.save()

            seed_bookable_hours(asset)
            seed_any_bookable_asset(asset)
            return redirect("accounts:organization_detail", organization_slug)
        else:
            print(form.errors())
    else:
        form = AssetForm()
    return render(request, "accounts/asset_create.html", {"form": form})


@login_required
def asset_update(request, asset_id):
    asset = get_object_or_404(
        Asset,
        id=asset_id,
    )
    organization = asset.organization
    permission_response = check_organization_permission(request, organization)
    if permission_response:
        return permission_response
    if request.method == "POST":
        form = AssetForm(request.POST, instance=asset)
        if form.is_valid():
            form.save()
            return redirect(
                "accounts:organization_detail",
                organization_slug=asset.organization.slug,
            )
    else:
        form = AssetForm(instance=asset)
    return render(
        request,
        "accounts/asset_update.html",
        {"form": form, "organization": organization},
    )


@login_required
def asset_delete(request, asset_id):
    asset = get_object_or_404(
        Asset,
        id=asset_id,
    )
    organization = asset.organization
    permission_response = check_organization_permission(request, organization)
    if permission_response:
        return permission_response
    if request.method == "POST":
        asset.delete()
        return HttpResponse("")


@login_required
def asset_config(request, asset_id):
    asset = get_object_or_404(
        Asset,
        id=asset_id,
    )
    organization = asset.organization
    permission_response = check_organization_permission(request, organization)
    if permission_response:
        return permission_response

    bookable_hours = AssetBookableHours.objects.filter(asset=asset)
    no_bookings = NoBookings.objects.filter(asset=asset, end_date__gte=date.today())
    context = {
        "bookable_hours": bookable_hours,
        "no_bookings": no_bookings,
        "asset": asset,
        "organization": organization,
    }
    return render(
        request,
        "accounts/asset_config.html",
        context,
    )


@login_required
def asset_bookable_hours_edit(request, asset_bookable_hours_id):
    bookable_hour = get_object_or_404(AssetBookableHours, id=asset_bookable_hours_id)
    permission_response = check_organization_permission(
        request, bookable_hour.asset.organization
    )
    if permission_response:
        return permission_response
    if request.method == "POST":
        print(request.POST)
        form = AssetBookableHoursForm(request.POST, instance=bookable_hour)
        if form.is_valid():
            bookable_hour = form.save()
            context = {"bookable_hour": bookable_hour}
            return render(request, "accounts/partials/bookable_hour.html", context)

    else:
        form = AssetBookableHoursForm(instance=bookable_hour)
    print(form)

    return render(
        request,
        "accounts/partials/bookable_hour_edit.html",
        {"form": form, "bookable_hour": bookable_hour},
    )


@login_required
def asset_bookable_hours_get(request, asset_bookable_hours_id):
    bookable_hour = get_object_or_404(AssetBookableHours, id=asset_bookable_hours_id)
    permission_response = check_organization_permission(
        request, bookable_hour.asset.organization
    )
    if permission_response:
        return permission_response

    context = {"bookable_hour": bookable_hour}
    return render(request, "accounts/partials/bookable_hour.html", context)


@login_required
def no_booking_add(request, asset_id):
    asset = get_object_or_404(Asset, id=asset_id)
    permission_response = check_organization_permission(request, asset.organization)
    if permission_response:
        return permission_response

    form = NoBookingsForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        no_booking = form.save(commit=False)
        no_booking.asset = asset

        # Fetch all overlapping bookings
        overlapping_bookings = Bookings.objects.filter(
            bookable_asset__asset=asset,
            date__range=(no_booking.start_date, no_booking.end_date),
        )

        # Check for overlapping accepted bookings
        overlapping_accepted_bookings = overlapping_bookings.filter(status="accepted")
        if overlapping_accepted_bookings.exists():
            form.add_error(
                None,
                ValidationError(
                    _(
                        "There are existing accepted bookings within the specified date range."
                    )
                ),
            )
        else:
            # Handle non-accepted overlapping bookings
            overlapping_non_accepted_bookings = overlapping_bookings.exclude(
                status="accepted"
            )

            if overlapping_non_accepted_bookings.exists():
                reject_bookings(overlapping_non_accepted_bookings)

            # Save the no_booking instance
            no_booking.save()
            context = {"no_booking": no_booking}
            return render(request, "accounts/partials/no_booking_day.html", context)

    context = {"form": form, "asset": asset}
    return render(request, "accounts/partials/no_booking_day_create_form.html", context)


@login_required
def no_booking_edit(request, no_booking_id):
    no_booking = get_object_or_404(NoBookings, id=no_booking_id)
    permission_response = check_organization_permission(
        request, no_booking.asset.organization
    )
    if permission_response:
        return permission_response

    if request.POST:
        form = NoBookingsForm(request.POST, instance=no_booking)
        if form.is_valid():
            form.save()
            context = {"no_booking": no_booking}
            return render(request, "accounts/partials/no_booking_day.html", context)
        else:
            print(form.errors)

    form = NoBookingsForm(instance=no_booking)
    context = {"form": form, "no_booking": no_booking}
    return render(request, "accounts/partials/no_booking_day_edit.html", context)


@login_required
def no_booking_get(request, no_booking_id):
    no_booking = get_object_or_404(NoBookings, id=no_booking_id)
    permission_response = check_organization_permission(
        request, no_booking.asset.organization
    )
    if permission_response:
        return permission_response

    context = {"no_booking": no_booking}
    return render(request, "accounts/partials/no_booking_day.html", context)


@login_required
def no_booking_delete(request, no_booking_id):
    if request.method == "POST":
        no_booking = get_object_or_404(NoBookings, id=no_booking_id)
        permission_response = check_organization_permission(
            request, no_booking.asset.organization
        )
        if permission_response:
            return permission_response
        no_booking.delete()

    return HttpResponse("")


# @login_required
# def create_bookable_asset(request):
#     if request.method == "POST":
#         form = BookableAssetForm(request.POST)
#         if form.is_valid():
#             form.save()
#             return redirect(
#                 "accounts:bookable_assets_list"
#             )  # Redirect to a list of bookable assets or another appropriate view
#     else:
#         form = BookableAssetForm()
#     return render(request, "create_bookable_asset.html", {"form": form})


@login_required
def bookable_assets(request, asset_id):
    asset = get_object_or_404(Asset, id=asset_id)
    organization = asset.organization
    permission_response = check_organization_permission(request, organization)
    if permission_response:
        return permission_response
    bookable_assets = BookableAsset.objects.filter(asset=asset_id)

    context = {
        "bookable_assets": bookable_assets,
        "asset": asset,
        "organization": organization,
    }
    return render(request, "accounts/bookable_assets.html", context)


@login_required
def bookable_asset_add(request, asset_id):
    asset = get_object_or_404(Asset, id=asset_id)
    permission_response = check_organization_permission(request, asset.organization)
    if permission_response:
        return permission_response
    form = BookableAssetForm(request.POST or None)

    if request.method == "POST":
        print("In the post")
        print(request.POST)
        if form.is_valid():
            bookable_asset = form.save(False)
            bookable_asset.asset = asset
            bookable_asset.save()
            context = {"bookable_asset": bookable_asset, "asset": asset}
            return render(request, "accounts/partials/bookable_asset.html", context)

    context = {"form": form, "asset": asset}
    return render(request, "accounts/partials/bookable_asset_create_form.html", context)


@login_required
def bookable_asset_edit(request, bookable_asset_id):
    bookable_asset = get_object_or_404(BookableAsset, id=bookable_asset_id)
    permission_response = check_organization_permission(
        request, bookable_asset.asset.organization
    )
    if permission_response:
        return permission_response

    if request.POST:
        print("in the post")
        form = BookableAssetForm(request.POST, instance=bookable_asset)
        if form.is_valid():
            print("form valid")
            form.save()
            context = {"bookable_asset": bookable_asset, "asset": bookable_asset.asset}
            return render(request, "accounts/partials/bookable_asset.html", context)
        else:
            print(form.errors)

    form = BookableAssetForm(instance=bookable_asset)
    context = {"form": form, "bookable_asset": bookable_asset}
    return render(request, "accounts/partials/bookable_asset_edit.html", context)


@login_required
def bookable_asset_get(request, bookable_asset_id):
    bookable_asset = get_object_or_404(BookableAsset, id=bookable_asset_id)
    permission_response = check_organization_permission(
        request, bookable_asset.asset.organization
    )
    if permission_response:
        return permission_response

    context = {"bookable_asset": bookable_asset, "asset": bookable_asset.asset}
    return render(request, "accounts/partials/bookable_asset.html", context)


@login_required
def bookable_asset_delete(request, bookable_asset_id):
    if request.method == "POST":
        bookable_asset = get_object_or_404(BookableAsset, id=bookable_asset_id)
        permission_response = check_organization_permission(
            request, bookable_asset.asset.organization
        )
        if permission_response:
            return permission_response

        bookable_asset.delete()

    return HttpResponse("")


@login_required
def manage_admins(request, organization_slug):
    organization = get_object_or_404(Organization, slug=organization_slug)
    permission_response = check_organization_permission(request, organization)
    if permission_response:
        return permission_response

    if request.user not in organization.members.all():
        return redirect("organization_detail", organization_slug=organization_slug)

    if request.method == "POST":
        form = AdminManagementForm(request.POST, instance=organization)
        if form.is_valid():
            form.save()
            return redirect("organization_detail", organization_slug=organization_slug)
    else:
        form = AdminManagementForm(instance=organization)
    return render(
        request,
        "accounts/manage_admins.html",
        {"form": form, "organization": organization},
    )


@login_required
def organization_detail(request, organization_slug):
    profile = request.user
    organization = get_object_or_404(
        Organization, slug=organization_slug, members=profile
    )
    permission_response = check_organization_permission(request, organization)
    if permission_response:
        return permission_response

    # Retrieve the members of the organization
    memberships = Membership.objects.select_related("user").filter(
        organization=organization
    )

    assets = Asset.objects.filter(organization=organization)

    context = {
        "organization": organization,
        "memberships": memberships,
        "assets": assets,
    }
    # return render(request, "password/password_reset_email.html", context)
    return render(request, "accounts/organization_detail.html", context)


@login_required
def organization_update(request, organization_slug):
    organization = get_object_or_404(
        Organization, slug=organization_slug, members=request.user
    )
    permission_response = check_organization_permission(request, organization)
    if permission_response:
        return permission_response

    if request.method == "POST":
        form = OrganizationForm(request.POST, instance=organization)
        if form.is_valid():
            form.save()
            return redirect(
                "accounts:organization_detail", organization_slug=organization.slug
            )
    else:
        form = OrganizationForm(instance=organization)
    return render(
        request,
        "accounts/organization_update.html",
        {"form": form, "organization": organization},
    )


@login_required
def organization_delete(request, organization_slug):

    organization = get_object_or_404(
        Organization,
        slug=organization_slug,
    )
    permission_response = check_organization_permission(request, organization)
    if permission_response:
        return permission_response

    organization.delete()
    return HttpResponse(
        "<div class='inline-flex items-center rounded-md shadow-sm'><h1 class='text-red-600'>Organization Deleted</h1></div>"
    )


@login_required
def organization_leave(request, organization_slug):
    user = request.user
    membership = get_object_or_404(
        Membership, organization__slug=organization_slug, user=user
    )

    member_memberships = Membership.objects.filter(user=user, role=Membership.MEMBER)

    accepted_membership = member_memberships.filter(status="accepted")
    invited_membership = member_memberships.filter(status="invited")
    pending_membership = member_memberships.filter(status="pending")

    accepted_membership = Organization.objects.filter(
        id__in=accepted_membership.values("organization_id")
    )
    invited_membership = Organization.objects.filter(
        id__in=invited_membership.values("organization_id")
    )
    pending_membership = Organization.objects.filter(
        id__in=pending_membership.values("organization_id")
    )

    return render(
        request,
        "accounts/partials/organization_membership_details_tables.html",
        {
            "accepted_membership": accepted_membership,
            "invited_membership": invited_membership,
            "pending_membership": pending_membership,
        },
    )


@login_required
def organization_reject(request, organization_slug):
    user = request.user
    membership = get_object_or_404(
        Membership, organization__slug=organization_slug, user=user
    )
    membership.delete()

    member_memberships = Membership.objects.filter(user=user, role=Membership.MEMBER)

    invited_membership = member_memberships.filter(status="invited")

    invited_membership = Organization.objects.filter(
        id__in=invited_membership.values("organization_id")
    )
    return render(
        request,
        "accounts/partials/organization_table_invited_member.html",
        {"invited_membership": invited_membership},
    )


@login_required
def invite_member(request, organization_slug):
    organization = get_object_or_404(Organization, slug=organization_slug)
    permission_response = check_organization_permission(request, organization)
    if permission_response:
        return permission_response

    if request.method == "POST":
        form = InviteMemberForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]
            existing_user = CustomUser.objects.filter(email=email).first()
            if existing_user:
                if not Membership.objects.filter(
                    user=existing_user, organization=organization
                ).exists():
                    print("Existing user")
                    # Create a membership for the existing user
                    membership = Membership.objects.create(
                        user=existing_user,
                        organization=organization,
                        status="invited",
                        is_approved=True,
                    )
            else:
                # Generate an invitation token for the new user
                token = str(uuid.uuid4())
                # Build the invitation URL
                invitation_url = request.build_absolute_uri(
                    reverse("accounts:claim_account", args=[token])
                )
                # Create a new user and set is_active to False
                user = CustomUser.objects.create(
                    username=token,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=False,
                )
                # Create a membership with the invitation token
                membership = Membership.objects.create(
                    user=user,
                    organization=organization,
                    status="invited",
                    is_approved=True,
                )
                # Send the invitation email
                print(
                    f"""You are invited to join {organization.name}
                    You have been invited to join {organization.name}. Please click the link to join: {invitation_url}"""
                )

            return redirect(
                "accounts:organization_detail", organization_slug=organization_slug
            )
    else:
        form = InviteMemberForm(initial={"organization": organization})
    return render(
        request,
        "accounts/membership_invite_member.html",
        {"form": form, "organization": organization},
    )


def claim_account(request, token):
    user = get_object_or_404(CustomUser, is_active=False, username=token)
    check_username_post_url = (
        f"/tad_book/accounts/check_username_invitation_token/{user.slug}/"
    )
    print(check_username_post_url)

    if request.method == "POST":
        form = RegisterForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True
            user.save()
            login(request, user)
            return redirect(
                "accounts:profile",
            )
    else:
        form = RegisterForm(instance=user, initial={"username": ""})

    return render(
        request,
        "accounts/membership_claim_account.html",
        {"form": form, "check_username_post_url": check_username_post_url},
    )


@login_required
def organization_join_request(request, organization_slug):
    if request.method == "POST":
        organization = Organization.objects.get(slug=organization_slug)
        Membership.objects.create(user=request.user, organization=organization)

    memberships = Membership.objects.filter(user=request.user)
    organizations_not_a_member_of = Organization.objects.exclude(
        id__in=memberships.values("organization_id")
    )

    return render(
        request,
        "accounts/partials/organization_table_join_request.html",
        {"organizations_not_a_member_of": organizations_not_a_member_of},
    )


@login_required
def approve_membership(request, membership_id):
    membership = get_object_or_404(Membership, id=membership_id)
    if request.user in membership.organization.members.all():
        membership.is_approved = True
        membership.status = "accepted"
        membership.save()
    return redirect(
        "accounts:organization_detail", organization_slug=membership.organization.slug
    )


@login_required
def accept_membership(request, organization_id):

    membership = get_object_or_404(
        Membership, organization__id=organization_id, user=request.user
    )
    membership.is_approved = True
    membership.status = "accepted"
    membership.save()

    member_memberships = Membership.objects.filter(role=Membership.MEMBER)

    accepted_membership = member_memberships.filter(status="accepted")
    invited_membership = member_memberships.filter(status="invited")
    pending_membership = member_memberships.filter(status="pending")

    accepted_membership = Organization.objects.filter(
        id__in=accepted_membership.values("organization_id")
    )
    invited_membership = Organization.objects.filter(
        id__in=invited_membership.values("organization_id")
    )
    pending_membership = Organization.objects.filter(
        id__in=pending_membership.values("organization_id")
    )

    context = {
        "accepted_membership": accepted_membership,
        "invited_membership": invited_membership,
        "pending_membership": pending_membership,
    }

    return render(
        request,
        "accounts/partials/organization_membership_details_tables.html",
        context,
    )


@login_required
def membership_update_view(request, pk):
    # Check permission
    membership = get_object_or_404(Membership, pk=pk)

    organization = membership.organization
    permission_response = check_organization_permission(request, organization)
    if permission_response:
        return permission_response
    organization_members = Membership.objects.filter(organization=organization)

    if request.method == "POST":
        form = MembershipForm(request.POST, instance=membership)
        if form.is_valid():
            role = form.cleaned_data["role"]

            if (
                role != "admin"
                and not organization_members.filter(role=Membership.ADMIN)
                .exclude(user=membership.user)
                .exists()
            ):
                form.add_error(
                    None,
                    ValidationError(_("There must always be at least one admin")),
                )
            else:
                form.save()
                return redirect(
                    "accounts:organization_detail",
                    organization_slug=membership.organization.slug,
                )
    else:
        form = MembershipForm(instance=membership)

    return render(
        request,
        "accounts/membership_update_view.html",
        {"form": form, "organization": organization, "membership": membership},
    )


@login_required
def membership_delete_view(request, membership_id):
    membership = get_object_or_404(Membership, id=membership_id)
    organization = membership.organization
    permission_response = check_organization_permission(request, organization)
    if permission_response:
        return permission_response

    if request.method == "POST":
        membership.delete()
        return HttpResponse("")  # Replace with your success URL


@login_required
def no_permission_view(request):
    return render(request, "no_permission.html")
