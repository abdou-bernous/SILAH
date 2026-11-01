from rest_framework.permissions import BasePermission


class IsHR(BasePermission):
    message = "Réservé aux gestionnaires RH."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_hr)


def can_review(user, employee):
    """HR can review anyone; a manager only their direct reports (never themselves)."""
    if user.is_hr:
        return True
    return employee.manager_id == user.id and employee.id != user.id
