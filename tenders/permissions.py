from rest_framework.permissions import SAFE_METHODS, BasePermission


class TenderPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.role in ["customer", "admin"]

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            if request.user.role == "supplier":
                return obj.status in ["published", "closed"] or obj.customer_id == request.user.id
            return True
        return request.user.role == "admin" or obj.customer_id == request.user.id


class LotPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.role in ["customer", "admin"]

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return request.user.role == "admin" or obj.tender.customer_id == request.user.id


class ApplicationPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.role in ["supplier", "customer", "admin"]

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == "admin":
            return True
        if user.role == "supplier":
            return obj.supplier_id == user.id
        if user.role == "customer":
            return obj.lot.tender.customer_id == user.id
        return False


class DocumentPermission(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == "admin":
            return True
        if user.role == "supplier":
            return obj.application.supplier_id == user.id
        if user.role == "customer":
            return obj.application.lot.tender.customer_id == user.id
        return False
