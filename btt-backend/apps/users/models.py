"""
apps/users/models.py
Custom User model — all system roles stored in a single table.
"""
import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_verified", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        OWNER = "owner", "Bike Owner"
        AUTHORITY = "authority", "Police Authority"
        COMMUNITY = "community", "Community Reporter"
        ADMIN = "admin", "System Admin"

    # Core identity
    full_name = models.CharField(max_length=100)
    cnic = models.CharField(max_length=15, unique=True, null=True, blank=True,
                            help_text="13-digit Pakistani CNIC — null for community reporters")
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, null=True, blank=True,
                             help_text="Required for Twilio SMS recovery notifications")

    # Role & status
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.OWNER)
    is_verified = models.BooleanField(default=False,
                                      help_text="Email verified — unverified users cannot file reports")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # Authority-specific
    badge_number = models.CharField(max_length=30, unique=True, null=True, blank=True,
                                    help_text="Police badge number — authority role only")
    city = models.CharField(max_length=80, null=True, blank=True,
                            help_text="Registered city — used to scope authority dashboard")

    # Email verification token
    email_verification_token = models.UUIDField(default=uuid.uuid4, editable=False)
    email_verification_token_expires = models.DateTimeField(null=True, blank=True)
    password_reset_token = models.UUIDField(null=True, blank=True)
    password_reset_token_expires = models.DateTimeField(null=True, blank=True)

    # Timestamps & soft delete
    created_at = models.DateTimeField(default=timezone.now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} <{self.email}> [{self.role}]"

    @property
    def is_owner(self):
        return self.role == self.Role.OWNER

    @property
    def is_authority(self):
        return self.role == self.Role.AUTHORITY

    @property
    def is_community(self):
        return self.role == self.Role.COMMUNITY

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.is_active = False
        self.save(update_fields=["deleted_at", "is_active"])


class AuditLog(models.Model):
    """
    Immutable audit trail — INSERT ONLY. Never UPDATE or DELETE rows here.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=100,
                              help_text="e.g. CREATED_REPORT, UPDATED_STATUS, LOGGED_RECOVERY")
    table_affected = models.CharField(max_length=50, null=True, blank=True)
    record_id = models.IntegerField(null=True, blank=True)
    old_value = models.JSONField(null=True, blank=True,
                                 help_text="Previous state — NULL on CREATE actions")
    new_value = models.JSONField(null=True, blank=True,
                                 help_text="New state — NULL on DELETE actions")
    ip_address = models.GenericIPAddressField(protocol="both", null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-created_at"]
        # Enforce immutability at DB level — no updates, no deletes
        managed = True

    def __str__(self):
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {self.user} — {self.action}"

    def save(self, *args, **kwargs):
        # Prevent updates — only new inserts allowed
        if self.pk:
            raise ValueError("AuditLog records are immutable and cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("AuditLog records cannot be deleted.")
