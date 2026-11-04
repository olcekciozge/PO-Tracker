"""Dashboard sayfaları için okuma sorguları. Hesaplama grades.scoring'den gelir."""
from courses.models import Enrollment
from grades.models import Grade
from grades.scoring import lo_score, po_score
from outcomes.models import LOPO, AssessmentLO, ProgramOutcome


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