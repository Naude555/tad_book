from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden
from accounts.models import Membership


def check_organization_permission(
    request, organization, required_role=Membership.ADMIN
):

    organization_members = Membership.objects.filter(organization=organization)

    if not organization_members.filter(user=request.user, role=required_role).exists():
        return HttpResponseForbidden(
            "You do not have permission to perform this action."
        )
    return None
