"""Import institutional user lists without forcing raw passwords into a CSV.

Example:
  python manage.py import_accounts users.csv --dry-run
  python manage.py import_accounts users.csv

New accounts have unusable passwords. An administrator must set a temporary
password via Django admin or implement the institution's invitation service.
"""

import csv
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import AuditLog, User


EXPECTED_COLUMNS = {"username", "role"}
OPTIONAL_COLUMNS = {
    "first_name", "last_name", "email", "student_number", "department_code",
}
ALLOWED_ROLES = {User.Role.STUDENT, User.Role.INSTRUCTOR, User.Role.HEAD}


class Command(BaseCommand):
    help = "Load CSV accounts safely; admin/superuser roles cannot be imported."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="UTF-8 CSV dosyası")
        parser.add_argument("--dry-run", action="store_true", help="Veritabanına yazma")
        parser.add_argument("--update-existing", action="store_true", help="Mevcut normal kullanıcıları güncelle")
        parser.add_argument("--delimiter", default=",", help="CSV ayıracı (varsayılan virgül)")

    def handle(self, *args, **options):
        path = Path(options["csv_path"])
        if not path.is_file():
            raise CommandError(f"Dosya bulunamadı: {path}")
        delimiter = options["delimiter"]
        if len(delimiter) != 1:
            raise CommandError("CSV ayıracı tek karakter olmalı.")

        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle, delimiter=delimiter)
                headers = set(reader.fieldnames or [])
                if not EXPECTED_COLUMNS.issubset(headers):
                    missing = ", ".join(sorted(EXPECTED_COLUMNS - headers))
                    raise CommandError(f"CSV zorunlu sütunları eksik: {missing}")
                extra_headers = headers - EXPECTED_COLUMNS - OPTIONAL_COLUMNS
                if extra_headers:
                    raise CommandError(
                        "Desteklenmeyen CSV sütunları: " + ", ".join(sorted(extra_headers))
                    )
                rows = list(reader)
                if any(None in row for row in rows):
                    raise CommandError("CSV satırlarında başlıktan fazla alan var.")
        except (UnicodeError, OSError, csv.Error) as exc:
            raise CommandError(f"CSV okunamadı: {exc}") from exc

        # Validation is completed before ANY writes. There is no half-import.
        seen_usernames = set()
        seen_emails = set()
        seen_student_numbers = set()
        prepared = []
        errors = []
        for line_number, row in enumerate(rows, start=2):
            username = (row.get("username") or "").strip()
            role = (row.get("role") or "").strip().lower()
            if not username:
                errors.append(f"Satır {line_number}: kullanıcı adı boş.")
                continue
            key = username.casefold()
            if key in seen_usernames:
                errors.append(f"Satır {line_number}: dosyada tekrar eden kullanıcı adı {username}.")
                continue
            seen_usernames.add(key)
            if role not in ALLOWED_ROLES:
                errors.append(f"Satır {line_number}: geçersiz veya yasaklı rol {role!r}.")
                continue

            found = get_user_model().objects.filter(username__iexact=username).first()
            if found and not options["update_existing"]:
                errors.append(f"Satır {line_number}: {username} zaten mevcut (güncelleme kapalı).")
                continue
            if found and (found.is_superuser or found.is_staff or found.role == User.Role.ADMIN):
                errors.append(f"Satır {line_number}: yönetici hesabı CSV ile güncellenemez.")
                continue

            user = found or get_user_model()(username=username)
            user.role = role
            for column in OPTIONAL_COLUMNS:
                if column in headers:
                    setattr(user, column, (row.get(column) or "").strip())
            if not found:
                user.is_staff = False
                user.is_superuser = False
                user.set_unusable_password()
            # full_clean() checks the database, not other uncommitted rows in
            # this CSV. Validate collisions inside the batch explicitly.
            email_key = (user.email or "").strip().casefold()
            number_key = (user.student_number or "").strip()
            if email_key and email_key in seen_emails:
                errors.append(f"Satır {line_number}: dosyada tekrar eden e-posta.")
                continue
            if number_key and number_key in seen_student_numbers:
                errors.append(f"Satır {line_number}: dosyada tekrar eden öğrenci numarası.")
                continue
            try:
                user.full_clean()
            except ValidationError as exc:
                errors.append(f"Satır {line_number} ({username}): {exc.message_dict}")
                continue
            if email_key:
                seen_emails.add(email_key)
            if number_key:
                seen_student_numbers.add(number_key)
            prepared.append((user, bool(found)))

        if errors:
            for error in errors[:30]:
                self.stderr.write(self.style.ERROR(error))
            raise CommandError(f"İçe aktarım iptal edildi; {len(errors)} doğrulama hatası bulundu.")

        created = sum(1 for _, exists in prepared if not exists)
        updated = sum(1 for _, exists in prepared if exists)
        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS(
                f"DRY RUN: {created} yeni, {updated} güncellenecek; veritabanına yazılmadı."
            ))
            return
        with transaction.atomic():
            for user, exists in prepared:
                if exists:
                    user.save(update_fields=[
                        "first_name", "last_name", "email", "student_number", "department_code", "role",
                    ])
                else:
                    user.save()
                AuditLog.objects.create(
                    actor=None,
                    target=user,
                    action=AuditLog.Action.USER_UPDATED if exists else AuditLog.Action.USER_CREATED,
                    metadata={"source": "csv", "role": user.role},
                )
        self.stdout.write(self.style.SUCCESS(
            f"Tamamlandı: {created} yeni, {updated} güncellendi. Yeni hesapların parolası yoktur."
        ))
