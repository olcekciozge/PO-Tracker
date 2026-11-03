"""Authentication identities and security events for PO Tracker.

Domain models (courses, grades, learning/program outcomes) intentionally do not
live here. They reference settings.AUTH_USER_MODEL to share one identity source.
"""

from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager as BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Preserve Django's username-based creation and enforce a sensible root role."""

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields["role"] = self.model.Role.ADMIN
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """One user can log into PO Tracker with one of four application roles.

    Django's superuser/staff permissions remain independent of the application
    role; setting role='admin' alone must not grant Django admin access.
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        HEAD = "head", "Bölüm Başkanı"
        INSTRUCTOR = "instructor", "Öğretim Elemanı"
        STUDENT = "student", "Öğrenci"

    role = models.CharField(
        "Kullanıcı rolü",
        max_length=12,
        choices=Role.choices,
        default=Role.STUDENT,
        db_index=True,
    )
    student_number = models.CharField(
        "Öğrenci numarası",
        max_length=20,
        blank=True,
        null=True,
        unique=True,
        help_text="Öğrenci değilse boş bırakılabilir.",
    )
    department_code = models.CharField(
        "Bölüm kodu",
        max_length=30,
        blank=True,
        db_index=True,
        help_text="Örnek: CSE, BME. Ders/PO uygulamasındaki bölüm koduyla eşleştirilir.",
    )

    objects = UserManager()

    def clean(self):
        super().clean()
        if self.email:
            self.email = self.email.strip().lower()
        self.student_number = (self.student_number or "").strip() or None
        self.department_code = (self.department_code or "").strip().upper()

        errors = {}
        if self.email:
            duplicate_email = type(self).objects.filter(email__iexact=self.email)
            if self.pk:
                duplicate_email = duplicate_email.exclude(pk=self.pk)
            if duplicate_email.exists():
                errors["email"] = "Bu e-posta adresi başka bir hesaba kayıtlı."
        if self.student_number and self.role != self.Role.STUDENT:
            errors["student_number"] = "Öğrenci numarası yalnızca öğrenci rolünde kullanılır."
        if self.role == self.Role.HEAD and not self.department_code:
            errors["department_code"] = "Bölüm başkanı için bölüm kodu gereklidir."
        if self.is_superuser and self.role != self.Role.ADMIN:
            errors["role"] = "Süper kullanıcının uygulama rolü yönetici olmalıdır."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # Empty values in a UNIQUE student_number column should be SQL NULL.
        self.student_number = (self.student_number or "").strip() or None
        self.department_code = (self.department_code or "").strip().upper()
        self.email = (self.email or "").strip().lower()
        return super().save(*args, **kwargs)

    @property
    def is_department_head(self):
        return self.role == self.Role.HEAD

    @property
    def is_instructor(self):
        return self.role == self.Role.INSTRUCTOR

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def display_name(self):
        return self.get_full_name().strip() or self.username

    def __str__(self):
        return f"{self.display_name} ({self.username})"


class AuditLog(models.Model):
    """Explicit business audit trail, never storing passwords or auth tokens.

    The user management service writes these records in the same transaction
    as the change. Authentication signals write login/logout records. The
    audit table should be read-only for normal administrators.
    """

    class Action(models.TextChoices):
        USER_CREATED = "user_created", "Hesap oluşturuldu"
        USER_UPDATED = "user_updated", "Hesap düzenlendi"
        USER_ACTIVATED = "user_activated", "Hesap aktifleştirildi"
        USER_DEACTIVATED = "user_deactivated", "Hesap pasifleştirildi"
        PROFILE_UPDATED = "profile_updated", "Profil güncellendi"
        PASSWORD_CHANGED = "password_changed", "Parola değiştirildi"
        LOGIN = "login", "Giriş yapıldı"
        LOGOUT = "logout", "Çıkış yapıldı"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="performed_account_actions",
        blank=True,
        null=True,
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="account_audit_entries",
        blank=True,
        null=True,
    )
    action = models.CharField(max_length=30, choices=Action.choices, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = "Hesap işlem kaydı"
        verbose_name_plural = "Hesap işlem kayıtları"
        indexes = [models.Index(fields=["action", "created_at"], name="acc_audit_action_time")]

    def __str__(self):
        return f"{self.get_action_display()} — {self.created_at:%Y-%m-%d %H:%M}"
