import csv
import io
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from accounts.models import AuditLog

User = get_user_model()
PASS = "AnExample-Strong-Password-123"


class ImportCommandTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "users.csv"

    def write_csv(self, rows, headers=None):
        headers = headers or [
            "username", "role", "first_name", "last_name", "email",
            "student_number", "department_code",
        ]
        with self.path.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

    def sample(self, **changes):
        row = {
            "username": "student002", "role": "student", "first_name": "Zeynep",
            "last_name": "Deneme", "email": "zeynep@example.edu",
            "student_number": "S002", "department_code": "CSE",
        }
        row.update(changes)
        return row

    def test_dry_run_does_not_create_user(self):
        self.write_csv([self.sample()])
        output = io.StringIO()
        call_command("import_accounts", str(self.path), dry_run=True, stdout=output)
        self.assertFalse(User.objects.filter(username="student002").exists())
        self.assertIn("DRY RUN", output.getvalue())

    def test_import_creates_unusable_password(self):
        self.write_csv([self.sample()])
        call_command("import_accounts", str(self.path), stdout=io.StringIO())
        user = User.objects.get(username="student002")
        self.assertEqual(user.department_code, "CSE")
        self.assertFalse(user.has_usable_password())
        self.assertEqual(user.email, "zeynep@example.edu")
        self.assertTrue(AuditLog.objects.filter(
            target=user, action=AuditLog.Action.USER_CREATED, metadata__source="csv"
        ).exists())

    def test_bad_role_is_rejected(self):
        self.write_csv([self.sample(role="admin")])
        with self.assertRaises(CommandError):
            call_command("import_accounts", str(self.path), stdout=io.StringIO(), stderr=io.StringIO())
        self.assertFalse(User.objects.filter(username="student002").exists())

    def test_missing_headers_are_rejected(self):
        self.write_csv([{"username": "student002"}], headers=["username"])
        with self.assertRaises(CommandError):
            call_command("import_accounts", str(self.path), stderr=io.StringIO())

    def test_duplicate_usernames_in_csv_rejected(self):
        self.write_csv([self.sample(), self.sample(email="other@example.edu")])
        with self.assertRaises(CommandError):
            call_command("import_accounts", str(self.path), stderr=io.StringIO())
        self.assertFalse(User.objects.filter(username="student002").exists())

    def test_existing_user_requires_update_existing(self):
        User.objects.create_user("student002", password=PASS)
        self.write_csv([self.sample()])
        with self.assertRaises(CommandError):
            call_command("import_accounts", str(self.path), stderr=io.StringIO())

    def test_update_existing_keeps_password(self):
        user = User.objects.create_user("student002", password=PASS, role=User.Role.STUDENT)
        self.write_csv([self.sample(first_name="Updated")])
        call_command(
            "import_accounts", str(self.path), update_existing=True,
            stdout=io.StringIO(),
        )
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Updated")
        self.assertTrue(user.check_password(PASS))

    def test_import_cannot_modify_superuser(self):
        User.objects.create_superuser("student002", password=PASS)
        self.write_csv([self.sample()])
        with self.assertRaises(CommandError):
            call_command(
                "import_accounts", str(self.path), update_existing=True,
                stderr=io.StringIO(),
            )

    def test_one_invalid_row_aborts_whole_file(self):
        self.write_csv([
            self.sample(),
            self.sample(username="illegal", role="admin", student_number="S003"),
        ])
        with self.assertRaises(CommandError):
            call_command("import_accounts", str(self.path), stderr=io.StringIO())
        self.assertFalse(User.objects.filter(username="student002").exists())

    def test_department_head_needs_department_code(self):
        self.write_csv([self.sample(role="head", student_number="", department_code="")])
        with self.assertRaises(CommandError):
            call_command("import_accounts", str(self.path), stderr=io.StringIO())

    def test_csv_accepts_tab_delimiter(self):
        self.write_csv([self.sample()])
        # Create an actual tab-delimited CSV for this test.
        with self.path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(self.sample()), delimiter="\t")
            writer.writeheader()
            writer.writerow(self.sample())
        call_command(
            "import_accounts", str(self.path), delimiter="\t", stdout=io.StringIO(),
        )
        self.assertTrue(User.objects.filter(username="student002").exists())

    def test_duplicate_emails_in_csv_are_rejected(self):
        self.write_csv([
            self.sample(),
            self.sample(username="student003", student_number="S003", email="ZEYNEP@example.edu"),
        ])
        with self.assertRaises(CommandError):
            call_command("import_accounts", str(self.path), stderr=io.StringIO())
        self.assertFalse(User.objects.filter(username="student002").exists())

    def test_duplicate_student_numbers_in_csv_are_rejected(self):
        self.write_csv([
            self.sample(),
            self.sample(username="student003", email="third@example.edu"),
        ])
        with self.assertRaises(CommandError):
            call_command("import_accounts", str(self.path), stderr=io.StringIO())
        self.assertFalse(User.objects.filter(username="student002").exists())

    def test_unknown_csv_columns_rejected(self):
        self.write_csv([{"username": "student", "role": "student", "password": "secret"}],
                       headers=["username", "role", "password"])
        with self.assertRaises(CommandError):
            call_command("import_accounts", str(self.path), stderr=io.StringIO())
