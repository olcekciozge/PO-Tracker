from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q


class Grade(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="grades",
    )
    assessment = models.ForeignKey(
        "courses.Assessment",
        on_delete=models.PROTECT,
        related_name="grades",
    )
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    class Meta:
        ordering = ["assessment", "student"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "assessment"],
                name="unique_grade_per_student_assessment",
            ),
            models.CheckConstraint(
                condition=Q(score__gte=0) & Q(score__lte=100),
                name="grade_score_between_0_and_100",
            ),
        ]

    def __str__(self):
        return f"{self.student} - {self.assessment}: {self.score}"