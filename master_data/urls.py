from django.urls import path
from .views import SpellCheckMedicine

urlpatterns = [
    path('check/', SpellCheckMedicine.as_view(), name='spell-check-medicine'),
]