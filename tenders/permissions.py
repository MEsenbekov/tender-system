from rest_framework.permissions import BasePermission, SAFE_METHODS


class TenderPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        return request.user.role in ['customer', 'admin']

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        return request.user.role == 'admin' or obj.customer == request.user


class ApplicationPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        return request.user.role in ['supplier', 'admin']

    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin':
            return True

        if request.user.role == 'supplier':
            return obj.supplier == request.user

        if request.user.role == 'customer':
            return obj.tender.customer == request.user

        return False


class DocumentPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin':
            return True

        if request.user.role == 'supplier':
            return obj.application.supplier == request.user

        if request.user.role == 'customer':
            return obj.application.tender.customer == request.user

        return False
