from django.urls import path
from accounts import views
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView

app_name = "accounts"

urlpatterns = [
    path("", views.IndexView.as_view(), name="home"),
    path("login/", views.Login.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/update/", views.profile_update_view, name="profile_update"),
    path(
        "password_reset/",
        auth_views.PasswordResetView.as_view(
            template_name="password/password_reset_form.html",
            html_email_template_name="password/password_reset_email.html",
        ),
        name="password_reset",
    ),
    path(
        "password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="password/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="password/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="password/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path(
        "password_change/",
        auth_views.PasswordChangeView.as_view(
            template_name="password/password_change_form.html"
        ),
    ),
    path(
        "password_change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="password/password_change_done.html"
        ),
    ),
    path("organization/", views.organization_views, name="organization"),
    path("organization/search/", views.organization_search, name="organization_search"),
    path("organization/create/", views.create_organization, name="create_organization"),
    path(
        "organization/<slug:organization_slug>/",
        views.organization_detail,
        name="organization_detail",
    ),
    path(
        "organization/<slug:organization_slug>/update/",
        views.organization_update,
        name="organization_update",
    ),
    # path("asset/", views.asset, name="asset"),
    path(
        "asset/<slug:organization_slug>/create/",
        views.asset_create,
        name="asset_create",
    ),
    # asset_update
    # # path(
    # #     "organization/<slug:organization_slug>/",
    # #     views.organization_detail,
    # #     name="organization_detail",
    # # ),
    path(
        "asset/<int:asset_id>/update/",
        views.asset_update,
        name="asset_update",
    ),
    path(
        "asset/<int:asset_id>/config/",
        views.asset_config,
        name="asset_config",
    ),
    path(
        "asset/<int:asset_id>/bookable_assets/",
        views.bookable_assets,
        name="bookable_assets",
    ),
    # path(
    #     "asset/<int:asset_id>/delete_bookable_asset/",
    #     views.delete_bookable_asset,
    #     name="delete_bookable_asset",
    # ),
    # path(
    #     "asset/<int:asset_id>/delete_bookable_asset/",
    #     views.delete_bookable_asset,
    #     name="delete_bookable_asset",
    # ),
    path(
        "organization/<slug:organization_slug>/manage_admins/",
        views.manage_admins,
        name="manage_admins",
    ),
    path(
        "organization/<slug:organization_slug>/invite/",
        views.invite_member,
        name="invite_member",
    ),
    path("claim-account/<uuid:token>/", views.claim_account, name="claim_account"),
    path(
        "organization/organization_join_request/<slug:organization_slug>/",
        views.organization_join_request,
        name="organization_join_request",
    ),
    path(
        "membership/<int:membership_id>/approve/",
        views.approve_membership,
        name="approve_membership",
    ),
    path(
        "membership/<int:pk>/update/",
        views.membership_update_view,
        name="membership_update",
    ),
    path("no_permission/", views.no_permission_view, name="no_permission"),
]

htmx_urlpatterns = [
    path("check_username/", views.check_username, name="check-username"),
    path(
        "check_username_invitation_token/<slug:user_slug>/",
        views.check_username_invitation_token,
        name="check_username_invitation_token",
    ),
    path(
        "get_invited_membership/",
        views.get_invited_membership,
        name="get_invited_membership",
    ),
    path(
        "get_all_membership/",
        views.get_all_membership,
        name="get_all_membership",
    ),
    path(
        "get_accepted_membership/",
        views.get_accepted_membership,
        name="get_accepted_membership",
    ),
    path(
        "organization/<slug:organization_slug>/delete/",
        views.organization_delete,
        name="organization_delete",
    ),
    path(
        "organization/<slug:organization_slug>/leave/",
        views.organization_leave,
        name="organization_leave",
    ),
    path(
        "organization/<slug:organization_slug>/reject/",
        views.organization_reject,
        name="organization_reject",
    ),
    path(
        "membership/<int:membership_id>/delete/",
        views.membership_delete_view,
        name="membership_delete",
    ),
    path(
        "membership/<int:organization_id>/accept/",
        views.accept_membership,
        name="accept_membership",
    ),
    path(
        "asset/<int:asset_id>/delete/",
        views.asset_delete,
        name="asset_delete",
    ),
    path(
        "asset/<int:asset_id>/bookable_asset_add/",
        views.bookable_asset_add,
        name="bookable_asset_add",
    ),
    path(
        "bookable_asset/<int:bookable_asset_id>/edit/",
        views.bookable_asset_edit,
        name="bookable_asset_edit",
    ),
    path(
        "bookable_asset/<int:bookable_asset_id>/get/",
        views.bookable_asset_get,
        name="bookable_asset_get",
    ),
    path(
        "bookable_asset/<int:bookable_asset_id>/delete/",
        views.bookable_asset_delete,
        name="bookable_asset_delete",
    ),
    path(
        "asset_bookable_hours/<int:asset_bookable_hours_id>/edit/",
        views.asset_bookable_hours_edit,
        name="asset_bookable_hours_edit",
    ),
    path(
        "asset_bookable_hours/<int:asset_bookable_hours_id>/get/",
        views.asset_bookable_hours_get,
        name="asset_bookable_hours_get",
    ),
    path(
        "asset/<int:asset_id>/no_bookings/",
        views.no_booking_add,
        name="no_booking_add",
    ),
    path(
        "no_bookings/<int:no_booking_id>/edit/",
        views.no_booking_edit,
        name="no_booking_edit",
    ),
    path(
        "no_bookings/<int:no_booking_id>/get/",
        views.no_booking_get,
        name="no_booking_get",
    ),
    path(
        "no_bookings/<int:no_booking_id>/delete/",
        views.no_booking_delete,
        name="no_booking_delete",
    ),
    path(
        "membership_tables/",
        views.membership_tables,
        name="membership_tables",
    ),
]

urlpatterns += htmx_urlpatterns
