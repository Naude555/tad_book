from django import forms
from accounts.models import BookableAsset
from bookings.models import Bookings, NoBookings


class NoBookingsForm(forms.ModelForm):
    class Meta:
        model = NoBookings
        fields = [
            "start_date",
            "end_date",
            "description",
        ]


class BookingForm(forms.ModelForm):
    class Meta:
        model = Bookings
        fields = ["date", "start_time", "end_time", "bookable_asset"]

    def __init__(self, *args, **kwargs):
        asset = kwargs.pop("asset", None)
        bookable_asset = kwargs.pop("bookable_asset", None)
        super().__init__(*args, **kwargs)

        if bookable_asset:
            self.fields["bookable_asset"] = forms.ModelChoiceField(
                queryset=BookableAsset.objects.filter(id=bookable_asset.id),
                initial=bookable_asset,
            )
        elif asset:
            self.fields["bookable_asset"] = forms.ModelChoiceField(
                queryset=BookableAsset.objects.filter(asset=asset)
            )
        else:
            self.fields["bookable_asset"] = forms.ModelChoiceField(
                queryset=BookableAsset.objects.none()
            )


class BookingFormAsset(forms.ModelForm):
    class Meta:
        model = Bookings
        fields = ["bookable_asset", "date", "start_time", "end_time", "status"]

    def __init__(self, *args, **kwargs):
        asset = kwargs.pop("asset", None)
        super().__init__(*args, **kwargs)

        if asset:
            self.fields["bookable_asset"] = forms.ModelChoiceField(
                queryset=BookableAsset.objects.filter(asset=asset),
                label="Bookable Asset",
                widget=forms.Select(attrs={"class": "form-control"}),
            )
        else:
            self.fields["bookable_asset"] = forms.ModelChoiceField(
                queryset=BookableAsset.objects.none(),
                label="Bookable Asset",
                widget=forms.Select(attrs={"class": "form-control"}),
            )

        # Update the labels in the dropdown
        self.fields["bookable_asset"].label_from_instance = self.label_from_instance

    def label_from_instance(self, obj):
        return f"{obj.name}"


class BookingFormOrganization(forms.ModelForm):
    class Meta:
        model = Bookings
        fields = ["bookable_asset", "date", "start_time", "end_time", "status"]

    def __init__(self, *args, **kwargs):
        asset = kwargs.pop("asset", None)
        super().__init__(*args, **kwargs)

        if asset:
            self.fields["bookable_asset"] = forms.ModelChoiceField(
                queryset=BookableAsset.objects.filter(asset=asset),
                label="Bookable Asset",
                widget=forms.Select(attrs={"class": "form-control"}),
            )
        else:
            self.fields["bookable_asset"] = forms.ModelChoiceField(
                queryset=BookableAsset.objects.none(),
                label="Bookable Asset",
                widget=forms.Select(attrs={"class": "form-control"}),
            )

        # Update the labels in the dropdown
        self.fields["bookable_asset"].label_from_instance = self.label_from_instance

    def label_from_instance(self, obj):
        return f"{obj.name}"


class AddParticipantForm(forms.Form):
    email = forms.EmailField(label="Participant Email")
