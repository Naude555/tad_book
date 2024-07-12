from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

app_name = "bookings"

urlpatterns = [
    path("organization/<slug:organization_slug>/", views.homepage, name="homepage"),
    # path(
    #     "admin/<slug:user_slug>/manage_bookings/",
    #     views.manage_bookings_admin,
    #     name="manage_bookings_admin",
    # ),
    path(
        "admin/<slug:user_slug>/manage_bookings/calendar/",
        views.manage_bookings_admin_calendar_view,
        name="manage_bookings_admin_calendar_view",
    ),
    path(
        "admin/<slug:user_slug>/manage_bookings/upcoming_list/",
        views.manage_bookings_admin_upcoming_list_view,
        name="manage_bookings_admin_upcoming_list_view",
    ),
    path(
        "organization/<slug:organization_slug>/manage_bookings/calendar/",
        views.manage_bookings_organization_calendar_view,
        name="manage_bookings_organization_calendar_view",
    ),
    path(
        "organization/<slug:organization_slug>/manage_bookings/upcoming_list_view/",
        views.manage_bookings_organization_upcoming_list_view,
        name="manage_bookings_organization_upcoming_list_view",
    ),
    path(
        "manage_bookings/admin/<int:booking_id>/edit/form/",
        views.manage_booking_admin_edit_form,
        name="manage_booking_admin_edit_form",
    ),
    path(
        "manage_bookings/organization/<int:booking_id>/edit/form/",
        views.manage_booking_organization_edit_form,
        name="manage_booking_organization_edit_form",
    ),
    # TODO: Add the following views
    path(
        "asset/<slug:asset_slug>/manage_bookings/calendar/",
        views.manage_bookings_asset_calendar_view,
        name="manage_bookings_asset_calendar_view",
    ),
    path(
        "asset/<slug:asset_slug>/manage_bookings/upcoming_list_view/",
        views.manage_bookings_asset_upcoming_list_view,
        name="manage_bookings_asset_upcoming_list_view",
    ),
    path(
        "bookable_asset/<slug:bookable_asset_slug>/manage_bookings/calendar/",
        views.manage_bookings_bookable_asset_calendar_view,
        name="manage_bookings_bookable_asset_calendar_view",
    ),
    path(
        "bookable_asset/<slug:bookable_asset_slug>/manage_bookings/calendar/share_link/",
        views.manage_bookings_bookable_asset_calendar_view_share_link,
        name="manage_bookings_bookable_asset_calendar_view_share_link",
    ),
    # TODO: Add the following views
    # path(
    #     "bookable_asset/<slug:bookable_asset_slug>/manage_bookings/upcoming_list_view/",
    #     views.manage_bookings_bookable_asset_upcoming_list_view,
    #     name="manage_bookings_bookable_asset_upcoming_list_view",
    # ),
    # path(
    #     "username/<slug:username_slug>/manage_bookings/",
    #     views.manage_bookings_user,
    #     name="manage_bookings_user",
    # ),
    path(
        "user/<slug:user_slug>/manage_bookings/calendar/",
        views.manage_bookings_user_calendar_view,
        name="manage_bookings_user_calendar_view",
    ),
    path(
        "username/<slug:user_slug>/manage_bookings/calendar/",
        views.manage_bookings_user_calendar_view,
        name="manage_bookings_user_calendar_view",
    ),
    path(
        "username/<slug:user_slug>/manage_bookings/upcoming_list/",
        views.manage_bookings_user_upcoming_list_view,
        name="manage_bookings_user_upcoming_list_view",
    ),
    path(
        "custom_booking/<slug:asset_slug>/",
        views.custom_booking,
        name="custom_booking",
    ),
    path("", views.index, name="index"),
    path("next/", views.next_month, name="next_month"),
    path("previous/", views.previous_month, name="previous_month"),
    path("today/", views.today, name="today"),
    path("modal/", views.modal, name="modal"),
    path("time_slots/", views.time_slots, name="time_slots"),
    path("events/", views.events, name="events"),
    path(
        "approve_booking/<int:booking_id>/<uuid:token>/",
        views.approve_booking,
        name="approve_booking",
    ),
    path(
        "reject_booking/<int:booking_id>/<uuid:token>/",
        views.reject_booking,
        name="reject_booking",
    ),
    path(
        "cancel_booking/<int:booking_id>/<uuid:token>/",
        views.cancel_booking,
        name="cancel_booking",
    ),
    path(
        "<int:booking_id>/participants/",
        views.booking_participants,
        name="booking_participants",
    ),
    path(
        "manage_bookings/view/<int:booking_id>/",
        views.manage_booking_view,
        name="manage_booking_view",
    ),
    path(
        "manage_bookings/view/<int:booking_id>/share_link/",
        views.manage_booking_view_share_link,
        name="manage_booking_view_share_link",
    ),
    path("test/", views.test, name="test"),
]

htmx_urlpatterns = [
    path("get_bookable_assets/", views.get_bookable_assets, name="get_bookable_assets"),
    path(
        "request_booking/<str:time_slot>/",
        views.request_booking,
        name="request_booking",
    ),
    path(
        "manage_bookings/admin/<int:booking_id>/edit/",
        views.manage_booking_admin_edit,
        name="manage_booking_admin_edit",
    ),
    path(
        "manage_bookings/admin/<int:booking_id>/get/",
        views.manage_booking_admin_get,
        name="manage_booking_admin_get",
    ),
    path(
        "manage_bookings/user/<int:booking_id>/cancel/",
        views.manage_booking_user_cancel,
        name="manage_booking_user_cancel",
    ),
    path(
        "manage_bookings/user/<int:booking_id>/get/",
        views.manage_booking_user_get,
        name="manage_booking_user_get",
    ),
    path(
        "manage_bookings/organization/<int:booking_id>/edit/",
        views.manage_booking_organization_edit,
        name="manage_booking_organization_edit",
    ),
    path(
        "manage_bookings/organization/<int:booking_id>/get/",
        views.manage_booking_organization_get,
        name="manage_booking_organization_get",
    ),
    path(
        "manage_bookings/asset/<int:booking_id>/edit/",
        views.manage_booking_asset_edit,
        name="manage_booking_asset_edit",
    ),
    path(
        "manage_bookings/asset/<int:booking_id>/get/",
        views.manage_booking_asset_get,
        name="manage_booking_asset_get",
    ),
    path(
        "<int:booking_id>/participant_add/",
        views.booking_participant_add,
        name="booking_participant_add",
    ),
    path(
        "<int:booking_id>/participant_remove/<int:user_id>/",
        views.booking_participant_remove,
        name="booking_participant_remove",
    ),
    path(
        "get_today_bookings/",
        views.get_today_bookings,
        name="get_today_bookings",
    ),
    path(
        "get_today_bookings_participants/",
        views.get_today_bookings_participants,
        name="get_today_bookings_participants",
    ),
    path(
        "upcomming_bookings_count/<int:organization_id>/",
        views.upcomming_bookings_count,
        name="upcomming_bookings_count",
    ),
    path(
        "today_upcomming_bookings_count/<int:organization_id>/",
        views.today_upcomming_bookings_count,
        name="today_upcomming_bookings_count",
    ),
    path(
        "current_bookings_count/<int:organization_id>/",
        views.current_bookings_count,
        name="current_bookings_count",
    ),
    path(
        "upcomming_pending_bookings_count/<int:organization_id>/",
        views.upcomming_pending_bookings_count,
        name="upcomming_pending_bookings_count",
    ),
]

urlpatterns += htmx_urlpatterns
