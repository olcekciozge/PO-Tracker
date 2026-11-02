from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q


class Course(models.Model):
    code = models.CharField(max_length=20)
    title = models.CharField(max_length=200)
    term = models.CharField(max_length=20)
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="taught_courses",
    )

    class Meta:
        ordering = ["code", "term"]
        constraints = [
            models.UniqueConstraint(
                fields=["code", "term"],
                name="unique_course_code_term",
            ),
        ]

    def __str__(self):
        return f"{self.code} {self.title} ({self.term})"


class Assessment(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="assessments",
    )
    name = models.CharField(max_length=100)
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    class Meta:
        ordering = ["course", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "name"],
                name="unique_assessment_name_per_course",
            ),
            models.CheckConstraint(
                condition=Q(weight__gte=0) & Q(weight__lte=100),
                name="assessment_weight_between_0_and_100",
            ),
        ]

    def __str__(self):
        return f"{self.course.code} - {self.name} ({self.weight}%)"




class Enrollment(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )

    class Meta:
        ordering = ["course", "student"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course"],
                name="unique_student_course_enrollment",
            ),
        ]

    def __str__(self):
        return f"{self.student} - {self.course}"