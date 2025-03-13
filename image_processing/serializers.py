from rest_framework import serializers
from image_processing.models import PrescriptionRecord


class PrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrescriptionRecord
        fields = ['id', 'patient_name', 'prescription_date', 'medications', 'complaints', 'gender', 'age', 'weight', 'bp', 'place', 'follow_up_date', 'date_created', 'date_updated'] # noqa
