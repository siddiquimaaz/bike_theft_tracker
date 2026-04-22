"""
apps/users/permissions.py
Role-Based Access Control permission classes for DRF.
Applied per-ViewSet to enforce the 4-role system.
"""
from rest_framework.permissions import BasePermission, IsAuthenticated


class IsVerifiedUser(IsAuthenticated):
    """User must be authenticated AND have verified their email."""
    message = "Email verification required before performing this action."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_verified


class IsOwner(IsVerifiedUser):
    """Only Bike Owners may access this resource."""
    message = "This endpoint is restricted to Bike Owners."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            if getattr(request, "user", None) and request.user.is_authenticated and not request.user.is_verified:
                self.message = IsVerifiedUser.message
            return False
        if not request.user.is_owner:
            self.message = "This endpoint is restricted to Bike Owners."
            return False
        return True


class IsAuthority(IsVerifiedUser):
    """Only Police Authority officers may access this resource."""
    message = "This endpoint is restricted to Authority Officers."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_authority


class IsCommunity(IsAuthenticated):
    """Community Reporters (email verification not required for sightings)."""
    message = "This endpoint is restricted to Community Reporters."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_community


class IsAdminUser(IsAuthenticated):
    """System Admin only."""
    message = "This endpoint is restricted to System Administrators."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_admin


class IsOwnerOrAuthority(IsVerifiedUser):
    """Owners or Authority officers."""
    def has_permission(self, request, view):
        return super().has_permission(request, view) and (
            request.user.is_owner or request.user.is_authority
        )


class IsAuthorityOrAdmin(IsAuthenticated):
    """Authority or Admin."""
    def has_permission(self, request, view):
        return super().has_permission(request, view) and (
            request.user.is_authority or request.user.is_admin
        )


class IsAnyAuthenticatedRole(IsAuthenticated):
    """Any authenticated user regardless of role."""
    pass


class IsResourceOwner(BasePermission):
    """
    Object-level: only the resource owner (user who created it) may modify it.
    Combine with role check at view level.
    """
    message = "You do not have permission to modify this resource."

    def has_object_permission(self, request, view, obj):
        # Allow reads to authenticated users, writes only to owner
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        owner_field_options = ("owner", "reported_by", "sighter", "user")
        for field in owner_field_options:
            if hasattr(obj, field) and getattr(obj, field) == request.user:
                return True
        return False
