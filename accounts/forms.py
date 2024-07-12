from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from .models import (
    Asset,
    AssetBookableHours,
    BookableAsset,
    CustomUser,
    Membership,
    Organization,
)


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)

    class Meta:
        model = CustomUser
        fields = ("username", "email", "first_name", "last_name")


class CustomUserChangeForm(UserChangeForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)

    class Meta:
        model = CustomUser
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "bio",
            "location",
            "birth_date",
        )


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = [
            "name",
            "asset_name",
            "exclusive_booking_accross_organization",
            "exclusive_booking_accross_asset",
        ]


class InviteMemberForm(forms.Form):
    email = forms.EmailField(label="Email")
    first_name = forms.CharField(max_length=50, required=False)
    last_name = forms.CharField(max_length=50, required=False)


class RequestAccessForm(forms.Form):
    organization = forms.ModelChoiceField(queryset=Organization.objects.all())


class SetPasswordForm(forms.Form):
    password = forms.CharField(label="Password", widget=forms.PasswordInput)


class AdminManagementForm(forms.ModelForm):
    members = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = Organization
        fields = ["members"]

    def clean_members(self):
        members = self.cleaned_data.get("members")
        if not members:
            raise forms.ValidationError("There must be at least one admin.")
        return members


class MembershipForm(forms.ModelForm):
    class Meta:
        model = Membership
        fields = ["role", "is_approved", "status"]


class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = [
            "name",
            "description",
            "bookable_asset_name",
            "default_booking_status",
            "slot_duration",
            "buffer_time",
            "max_days_ahead",
            "admin_assigns_booking",
        ]


class BookableAssetForm(forms.ModelForm):
    class Meta:
        model = BookableAsset
        fields = [
            "name",
            "calendar_colour",
            "share_link",
        ]


class AssetBookableHoursForm(forms.ModelForm):
    class Meta:
        model = AssetBookableHours
        fields = [
            "start_time",
            "end_time",
            "is_active",
        ]
