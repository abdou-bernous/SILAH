"""Multi-company access rules.

Every request works on one *active company*:
  - employees, managers and HR users: their own company, always;
  - accountants: one of the companies they manage, chosen with the `X-Company` header
    (defaults to the first one);
  - the platform admin: none. It is a system administrator (companies, accounts, global
    figures) and has no access to employee records or payroll.

"Company admin" rights (payroll, employee records, documents, validations) are granted on
the active company to its HR users and to the accountants who manage it. A deactivated
company is closed: its members can no longer use the API.
"""
from rest_framework.permissions import BasePermission, IsAuthenticated

from .models import Company, User


def managed_companies(user):
    """Companies on which `user` has HR-level rights."""
    if not user or not user.is_authenticated:
        return Company.objects.none()
    if user.role == User.Role.ACCOUNTANT:
        return user.managed_companies.all()
    if user.role == User.Role.HR and user.company_id:
        return Company.objects.filter(id=user.company_id)
    return Company.objects.none()


def visible_companies(user):
    """Companies `user` can list and edit as companies (not their employees)."""
    if user.is_platform_admin:
        return Company.objects.all()
    if user.role == User.Role.ACCOUNTANT:
        return user.managed_companies.all()
    return Company.objects.none()


def active_company(request):
    if hasattr(request, '_silah_company'):
        return request._silah_company
    user = request.user
    company = None
    raw = request.headers.get('X-Company', '')
    if raw.isdigit() and user.is_hr:
        company = managed_companies(user).filter(id=int(raw), is_active=True).first()
    if company is None:
        if user.company_id:
            company = user.company
        else:
            company = managed_companies(user).filter(is_active=True).order_by('name').first()
    request._silah_company = company
    return company


def is_company_admin(request, company=None):
    company = company or active_company(request)
    if company is None:
        return False
    return managed_companies(request.user).filter(id=company.id).exists()


def hr_recipients(company):
    """People told about new requests that have no manager: HR of the company and its accountants."""
    if company is None:
        return []
    hr = list(User.objects.filter(company=company, role=User.Role.HR, is_active=True))
    return hr + list(company.managers.filter(is_active=True).exclude(id__in=[u.id for u in hr]))


class IsActiveMember(IsAuthenticated):
    """Default permission: authenticated, and not a member of a deactivated company."""
    message = "Le compte de votre entreprise est désactivé."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        user = request.user
        return user.company_id is None or Company.objects.filter(id=user.company_id, is_active=True).exists()


class IsCompanyAdmin(BasePermission):
    message = "Réservé à la gestion RH de l'entreprise."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and is_company_admin(request))


class IsPlatformAdmin(BasePermission):
    message = "Réservé à l'administrateur de la plateforme."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_platform_admin)


class CanManageCompanies(BasePermission):
    """Accountants and the platform admin create and edit companies."""
    message = 'Réservé aux comptables et à l\'administrateur.'

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.is_platform_admin or u.role == User.Role.ACCOUNTANT))


# Backwards-compatible name used by the views.
IsHR = IsCompanyAdmin


def can_review(request, employee):
    """Company admins review anyone of the active company; a manager only their direct reports."""
    user = request.user
    if employee.id == user.id:
        return False
    company = active_company(request)
    if company and employee.company_id == company.id and is_company_admin(request):
        return True
    return employee.manager_id == user.id
