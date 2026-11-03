"""Controlled forms: profile users cannot submit hidden role or staff fields."""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError

from .models import User
from .permissions import can_assign_role


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Kullanıcı adı",
        widget=forms.TextInput(attrs={"autocomplete": "username", "autofocus": True}),
    )
    password = forms.CharField(
        label="Parola",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )


class IdentityValidationMixin:
    """Both the create and update forms require consistent identity fields."""

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if email:
            existing = User.objects.filter(email__iexact=email)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise ValidationError("Bu e-posta adresi başka bir kullanıcı tarafından kullanılıyor.")
        return email

    def clean_student_number(self):
        return (self.cleaned_data.get("student_number") or "").strip() or None

    def clean_department_code(self):
        return (self.cleaned_data.get("department_code") or "").strip().upper()

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")
        number = cleaned.get("student_number")
        department = cleaned.get("department_code")
        if role and role != User.Role.STUDENT and number:
            self.add_error("student_number", "Yalnızca öğrencilerin öğrenci numarası olabilir.")
        if role == User.Role.HEAD and not department:
            self.add_error("department_code", "Bölüm başkanına bir bölüm kodu atayın.")
        return cleaned


class AccountCreateForm(IdentityValidationMixin, UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "username", "first_name", "last_name", "email",
            "role", "student_number", "department_code",
        )
        labels = {
            "username": "Kullanıcı adı", "first_name": "Ad", "last_name": "Soyad",
            "email": "E-posta", "role": "Sistem rolü",
        }

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        if not getattr(actor, "is_superuser", False):
            self.fields["role"].choices = [
                item for item in User.Role.choices if item[0] != User.Role.ADMIN
            ]
        self.fields["username"].widget.attrs["autocomplete"] = "off"
        self.fields["email"].widget.attrs["autocomplete"] = "off"

    def clean_username(self):
        username = super().clean_username()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("Bu kullanıcı adı zaten kullanılıyor.")
        return username

    def clean_role(self):
        role = self.cleaned_data["role"]
        if not can_assign_role(self.actor, role):
            raise ValidationError("Bu rolü atamaya yetkiniz bulunmuyor.")
        return role


class AccountUpdateForm(IdentityValidationMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = (
            "first_name", "last_name", "email", "role",
            "student_number", "department_code",
        )
        labels = {"first_name": "Ad", "last_name": "Soyad", "email": "E-posta"}

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        if not getattr(actor, "is_superuser", False):
            self.fields["role"].choices = [
                item for item in User.Role.choices if item[0] != User.Role.ADMIN
            ]

    def clean_role(self):
        role = self.cleaned_data["role"]
        if not can_assign_role(self.actor, role):
            raise ValidationError("Bu rolü atamaya yetkiniz bulunmuyor.")
        if self.instance.is_superuser and role != User.Role.ADMIN:
            raise ValidationError("Süper kullanıcının rolü değiştirilemez.")
        return role


class ProfileForm(IdentityValidationMixin, forms.ModelForm):
    """Whitelist personal fields only. No role/department/student-number edits."""

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")
        labels = {"first_name": "Ad", "last_name": "Soyad", "email": "E-posta"}


class UserSearchForm(forms.Form):
    q = forms.CharField(required=False, max_length=100, label="Ara")
    role = forms.ChoiceField(
        required=False, choices=[("", "Tüm roller"), *User.Role.choices], label="Rol"
    )
    status = forms.ChoiceField(
        required=False,
        choices=[("", "Tüm durumlar"), ("active", "Aktif"), ("inactive", "Pasif")],
        label="Durum",
    )
