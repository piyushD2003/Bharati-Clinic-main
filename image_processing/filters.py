import django_filters
from image_processing.models import PrescriptionRecord


class PrescriptionRecordFilter(django_filters.FilterSet):
    id = django_filters.NumberFilter(field_name='id', lookup_expr='exact')
    patient_name = django_filters.CharFilter(lookup_expr='startswith')
    prescription_date = django_filters.DateFilter(field_name='prescription_date', lookup_expr='exact')
    gender = django_filters.ChoiceFilter(field_name='gender', choices=[("M", "Male"), ("F", "Female")])

    class Meta:
        model = PrescriptionRecord
        fields = ['id', 'patient_name', 'prescription_date','gender']
