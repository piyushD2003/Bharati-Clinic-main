from django.db import models


class PrescriptionRecord(models.Model):
    patient_name = models.CharField(
        max_length=50,
        verbose_name="Patient Name",
        blank=True
    )

    prescription_date = models.DateField(
        verbose_name="Prescription Date",
        blank=True,
        null=True
    )

    medications = models.JSONField(
        default=list,
        verbose_name="Medications"
    )

    complaints = models.JSONField(
        default=list,
        verbose_name="Complaints"
    )

    gender = models.CharField(
        max_length=50,
        verbose_name="Gender",
        blank=True
    )

    age = models.CharField(
        max_length=50,
        verbose_name="Age",
        blank=True
    )

    weight = models.CharField(
        max_length=50,
        verbose_name="Weight",
        blank=True
    )

    bp = models.CharField(
        max_length=50,
        verbose_name="BP",
        blank=True
    )

    place = models.CharField(
        max_length=50,
        verbose_name="Place",
        blank=True
    )

    follow_up_date = models.DateField(
        verbose_name="Follow up date",
        blank=True,
        null=True
    )

    date_created = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date Created"
    )

    date_updated = models.DateTimeField(
        auto_now=True,
        verbose_name="Date Updated"
    )

    class Meta:
        db_table = "PrescriptionRecord"
        verbose_name = "Prescription Record"
        verbose_name_plural = "Prescription Record"

    def __str__(self):
        return self.patient_name
