"""Hocanın sunumundaki Elif örneğini veritabanına kurar: python manage.py seed_demo"""
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from courses.models import Assessment, Course, Enrollment
from grades.models import Grade
from outcomes.models import LOPO, AssessmentLO, LearningOutcome, ProgramOutcome

DEMO_PASSWORD = "demo-pass-2026"

PROGRAM_OUTCOMES = [
    "Matematik, fen ve mühendislik bilgisi",
    "Mühendislik problemlerini tanımlama, modelleme ve çözme",
    "Gerçekçi kısıtlar altında sistem tasarlama",
    "Modern teknik, araç ve bilişim teknolojilerini kullanma",
    "Deney tasarlama, yürütme ve veri analizi",
    "Disiplin içi ve disiplinler arası takım çalışması",
    "Sözlü ve yazılı etkili iletişim",
    "Yaşam boyu öğrenme",
    "Etik ve mesleki sorumluluk",
    "Proje, risk ve değişim yönetimi; girişimcilik",
    "Mühendislik uygulamalarının sağlık, çevre, güvenlik ve hukuki etkileri",
]


def demo_user(username, first_name, last_name, role):
    user, created = User.objects.get_or_create(
        username=username,
        defaults={"first_name": first_name, "last_name": last_name, "role": role},
    )
    if created:
        user.set_password(DEMO_PASSWORD)
        user.save()
    return user


class Command(BaseCommand):
    help = "Elif örneğiyle demo verisi oluşturur (tekrar çalıştırmak güvenlidir)."

    @transaction.atomic
    def handle(self, *args, **options):
        pos = {}
        for number, description in enumerate(PROGRAM_OUTCOMES, start=1):
            pos[number], _ = ProgramOutcome.objects.get_or_create(
                code=f"PO{number}", defaults={"description": description}
            )

        instructor = demo_user("demo.hoca", "Demo", "Hoca", User.Role.INSTRUCTOR)
        elif_ = demo_user("elif", "Elif", "Yılmaz", User.Role.STUDENT)
        can = demo_user("can", "Can", "Demir", User.Role.STUDENT)

        course, _ = Course.objects.get_or_create(
            code="CSE 311", term="Güz 2026",
            defaults={"title": "Software", "instructor": instructor},
        )

        assessments = {}
        for name, weight in [("Ara Sınav I", 25), ("Ara Sınav II", 25), ("Devam ve Katılım", 10), ("Proje", 40)]:
            assessments[name], _ = Assessment.objects.update_or_create(
                course=course, name=name, defaults={"weight": weight}
            )

        los = {}
        for code, description in [
            ("LO1", "Yaygın yazılım geliştirme pratiklerinin ardındaki tasarım tercihleri"),
            ("LO2", "Çevik yazılım geliştirme yöntemi, iyi pratikler ve takım becerileri"),
            ("LO3", "Bu becerileri bir takım projesinde uygulama"),
            ("LO4", "Deneyimi anlatan dönem raporu yazma"),
        ]:
            los[code], _ = LearningOutcome.objects.get_or_create(
                course=course, code=code, defaults={"description": description}
            )

        # Hocanın örneği: Ara sınav %60 + Proje %40 → LO1, Ara sınav %40 + Proje %100 → LO2
        for assessment, lo, weight in [
            ("Ara Sınav I", "LO1", 60), ("Proje", "LO1", 40),
            ("Ara Sınav I", "LO2", 40), ("Proje", "LO2", 100),
        ]:
            AssessmentLO.objects.update_or_create(
                assessment=assessments[assessment], lo=los[lo], defaults={"weight": weight}
            )

        # LO1 → PO1 tam katkı (2), LO2 → PO1 yarım katkı (1), LO2 → PO2 tam katkı (2)
        for lo, po, weight in [("LO1", 1, 2), ("LO2", 1, 1), ("LO2", 2, 2)]:
            LOPO.objects.update_or_create(lo=los[lo], po=pos[po], defaults={"weight": weight})

        for student, scores in [(elif_, {"Ara Sınav I": 90, "Proje": 80}), (can, {"Ara Sınav I": 95, "Proje": 92})]:
            Enrollment.objects.get_or_create(student=student, course=course)
            for name, score in scores.items():
                Grade.objects.update_or_create(
                    student=student, assessment=assessments[name], defaults={"score": score}
                )

        self.stdout.write(self.style.SUCCESS(
            f"Demo verisi hazır. Giriş: elif / can / demo.hoca, parola: {DEMO_PASSWORD}"
        ))