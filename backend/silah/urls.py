from django.contrib import admin
from django.urls import include, path

admin.site.site_header = 'SILAH — administration'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    # Stable prefix for the future mobile app: an installed version keeps calling the same contract.
    path('api/v1/', include('api.urls')),
]
# Uploaded files are deliberately NOT served under /media/: payslips, documents
# and receipts are confidential and only go out through authenticated API actions.
