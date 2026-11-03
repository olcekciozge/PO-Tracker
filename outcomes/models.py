from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q


class ProgramOutcome(models.Model):
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField()

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.code


class LearningOutcome(models.Model):
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="learning_outcomes",
    )
    code = models.CharField(max_length=10)
    description = models.TextField()

    class Meta:
        ordering = ["course", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "code"],
                name="unique_lo_code_per_course",
            ),
        ]

    def __str__(self):
        return f"{self.course.code} {self.code}"


class AssessmentLO(models.Model):
    assessment = models.ForeignKey(
        "courses.Assessment",
        on_delete=models.CASCADE,
        related_name="lo_links",
    )
    lo = models.ForeignKey(
        LearningOutcome,
        on_delete=models.CASCADE,
        related_name="assessment_links",
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["assessment", "lo"],
                name="unique_assessment_lo_link",
            ),
            models.CheckConstraint(
                condition=Q(weight__gte=0) & Q(weight__lte=100),
                name="assessment_lo_weight_between_0_and_100",
            ),
        ]

    def __str__(self):
        return f"{self.assessment} -> {self.lo} ({self.weight}%)"


class LOPO(models.Model):
    lo = models.ForeignKey(
        LearningOutcome,
        on_delete=models.CASCADE,
        related_name="po_links",
    )
    po = models.ForeignKey(
        ProgramOutcome,
        on_delete=models.PROTECT,
        related_name="lo_links",
    )
    weight = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["lo", "po"],
                name="unique_lo_po_link",
            ),
            models.CheckConstraint(
                condition=Q(weight__gte=1) & Q(weight__lte=5),
                name="lo_po_weight_between_1_and_5",
            ),
        ]

    def __str__(self):
        return f"{self.lo} -> {self.po} ({self.weight})"