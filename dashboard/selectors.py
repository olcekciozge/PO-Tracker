"""Dashboard sayfaları için okuma sorguları. Hesaplama grades.scoring'den gelir."""
from django.db.models import Count, Sum

from courses.models import Assessment, Course, Enrollment
from grades.models import Grade
from grades.scoring import lo_score, po_score
from outcomes.models import LOPO, AssessmentLO, LearningOutcome, ProgramOutcome


def student_po_profile(student, term=None):
    enrollments = Enrollment.objects.filter(student=student).select_related("course")
    if term:
        enrollments = enrollments.filter(course__term=term)
    courses = [enrollment.course for enrollment in enrollments]

    grades = {
        grade.assessment_id: float(grade.score)
        for grade in Grade.objects.filter(student=student, assessment__course__in=courses)
    }

    # LO skoru = kendisini besleyen değerlendirmelerin ağırlıklı ortalaması
    contributions = {}
    for link in AssessmentLO.objects.filter(lo__course__in=courses):
        contributions.setdefault(link.lo_id, {})[link.assessment_id] = float(link.weight)
    lo_scores = {lo_id: lo_score(parts, grades) for lo_id, parts in contributions.items()}

    # PO skoru = bağlı LO'ların 1–5 ağırlıklı ortalaması
    po_links = {}
    breakdown = {}
    for link in LOPO.objects.filter(lo__course__in=courses).select_related("lo", "lo__course"):
        po_links.setdefault(link.po_id, {})[link.lo_id] = link.weight
        breakdown.setdefault(link.po_id, []).append({
            "course": link.lo.course,
            "lo": link.lo,
            "weight": link.weight,
            "score": lo_scores.get(link.lo_id),
        })

    pos = [
        {
            "po": po,
            "score": po_score(po_links.get(po.id, {}), lo_scores),
            "breakdown": breakdown.get(po.id, []),
        }
        for po in ProgramOutcome.objects.all()
    ]

    course_rows = []
    for course in courses:
        assessment_ids = list(course.assessments.values_list("id", flat=True))
        graded = sum(1 for assessment_id in assessment_ids if assessment_id in grades)
        total = len(assessment_ids)
        course_rows.append({
            "course": course,
            "graded": graded,
            "total": total,
            "percent": round(100 * graded / total) if total else 0,
        })

    terms = sorted(set(
        Enrollment.objects.filter(student=student).values_list("course__term", flat=True)
    ))
    return {"pos": pos, "courses": course_rows, "terms": terms}


def instructor_courses(instructor):
    """Eğitmenin dersleri: sayılar, girilen notlar ve kurulum kontrol listesi."""
    courses = list(
        Course.objects.filter(instructor=instructor)
        .annotate(
            student_count=Count("enrollments", distinct=True),
            assessment_count=Count("assessments", distinct=True),
            lo_count=Count("learning_outcomes", distinct=True),
        )
        .order_by("code", "term")
    )

    def per_course(queryset, value):
        return {row["course"]: row["value"] for row in queryset.values("course").annotate(value=value)}

    weight_totals = per_course(Assessment.objects.filter(course__in=courses), Sum("weight"))
    unlinked_assessments = per_course(
        Assessment.objects.filter(course__in=courses, lo_links__isnull=True), Count("id")
    )
    unlinked_los = per_course(
        LearningOutcome.objects.filter(course__in=courses, po_links__isnull=True), Count("id")
    )
    grade_counts = {
        row["assessment__course"]: row["value"]
        for row in Grade.objects.filter(assessment__course__in=courses)
        .values("assessment__course")
        .annotate(value=Count("id"))
    }

    cards = []
    for course in courses:
        weight_total = float(weight_totals.get(course.id) or 0)
        checks = [
            {"label": "Değerlendirme ağırlıkları toplam %100",
             "ok": course.assessment_count > 0 and abs(weight_total - 100) < 0.01},
            {"label": "Öğrenme çıktıları (LO) tanımlı",
             "ok": course.lo_count > 0},
            {"label": "Her değerlendirme bir LO'ya bağlı",
             "ok": course.assessment_count > 0 and not unlinked_assessments.get(course.id)},
            {"label": "Her LO bir program çıktısına (PO) bağlı",
             "ok": course.lo_count > 0 and not unlinked_los.get(course.id)},
        ]
        graded = grade_counts.get(course.id, 0)
        expected = course.student_count * course.assessment_count
        cards.append({
            "course": course,
            "checks": checks,
            "setup_ok": all(check["ok"] for check in checks),
            "graded": graded,
            "expected": expected,
        })
    return cards