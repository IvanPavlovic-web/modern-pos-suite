from rest_framework.permissions import BasePermission


class IsCashier(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser or request.user.groups.filter(name='cashier').exists()
        )


class IsManagerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser
            or request.user.groups.filter(name__in=['manager', 'admin']).exists()
        )


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser or request.user.groups.filter(name='admin').exists()
        )


class IsCashierOrHigher(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser
            or request.user.groups.filter(name__in=['cashier', 'manager', 'admin']).exists()
        )