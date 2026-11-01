from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

router = DefaultRouter()
router.register('employees', views.EmployeeViewSet, basename='employee')
router.register('payslips', views.PayslipViewSet, basename='payslip')
router.register('documents', views.DocumentViewSet, basename='document')
router.register('leaves', views.LeaveRequestViewSet, basename='leave')
router.register('expenses', views.ExpenseViewSet, basename='expense')
router.register('profile-requests', views.ProfileChangeRequestViewSet, basename='profile-request')
router.register('notifications', views.NotificationViewSet, basename='notification')
router.register('pay-items', views.EmployeePayItemViewSet, basename='pay-item')
router.register('certificates', views.CertificateRequestViewSet, basename='certificate')
router.register('audit', views.AuditLogViewSet, basename='audit')
router.register('companies', views.CompanyViewSet, basename='company-admin')
router.register('platform/users', views.PlatformUserViewSet, basename='platform-user')

urlpatterns = [
    path('', include(router.urls)),
    path('health/', views.HealthView.as_view(), name='health'),
    path('auth/login/', views.LoginView.as_view(), name='token_obtain'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', views.MeView.as_view(), name='me'),
    path('auth/change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    path('auth/password-reset/', views.PasswordResetRequestView.as_view(), name='password-reset'),
    path('auth/password-reset/confirm/', views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('company/', views.CompanyView.as_view(), name='company'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('platform/stats/', views.PlatformStatsView.as_view(), name='platform-stats'),
]
