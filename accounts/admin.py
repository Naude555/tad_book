from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import RegisterForm, CustomUserChangeForm
from .models import Asset, AssetBookableHours, Config, CustomUser, Membership


class CustomUserAdmin(UserAdmin):
    # Define the fields to be used in displaying the CustomUser model.
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Personal info",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "bio",
                    "location",
                    "birth_date",
                    "phone",
                    "timezone",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
        ("Additional info", {"fields": ("can_start_own_organizations", "slug")}),
    )

    # Add fields to be used in forms
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "password1", "password2"),
            },
        ),
    )

    # Fields to be displayed in the admin list view
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
        "slug",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("username",)
    filter_horizontal = (
        "groups",
        "user_permissions",
    )


admin.site.register(CustomUser, CustomUserAdmin)

admin.site.register(Membership)

admin.site.register(Config)

admin.site.register(Asset)

admin.site.register(AssetBookableHours)
