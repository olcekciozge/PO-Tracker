"""Add department scoping and audit table without replacing original 0001."""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="department_code",
            field=models.CharField(blank=True, db_index=True, help_text="Örnek: CSE, BME. Ders/PO uygulamasındaki bölüm koduyla eşleştirilir.", max_length=30, verbose_name="Bölüm kodu"),
        ),
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(choices=[("user_created", "Hesap oluşturuldu"), ("user_updated", "Hesap düzenlendi"), ("user_activated", "Hesap aktifleştirildi"), ("user_deactivated", "Hesap pasifleştirildi"), ("profile_updated", "Profil güncellendi"), ("password_changed", "Parola değiştirildi"), ("login", "Giriş yapıldı"), ("logout", "Çıkış yapıldı")], db_index=True, max_length=30)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now, editable=False)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="performed_account_actions", to=settings.AUTH_USER_MODEL)),
                ("target", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="account_audit_entries", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Hesap işlem kaydı", "verbose_name_plural": "Hesap işlem kayıtları", "ordering": ("-created_at", "-pk")},
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["action", "created_at"], name="acc_audit_action_time"),
        ),
    ]
