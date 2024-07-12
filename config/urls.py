from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path("", include("home.urls")),
    path("tad_book/accounts/", include("accounts.urls")),
    path("tad_book/accounts/", include("django.contrib.auth.urls")),
    path("tad_book/bookings/", include("bookings.urls")),
    path("tad_book/admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
