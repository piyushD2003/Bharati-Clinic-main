from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import MedicineData
from rapidfuzz import process, fuzz


class SpellCheckMedicine(APIView):
    def post(self, request):
        extracted_medicines = request.data  # Get JSON object
        
        if not isinstance(extracted_medicines, dict):
            return Response({"error": "Invalid input format. Expected JSON object."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Fetch all medicine names from the database
        medicine_list = list(MedicineData.objects.values_list("name", flat=True))

        # Function to correct names
        def correct_medicines(extracted_medicines, medicine_list, threshold=50):
            corrected_medicines = {}

            for key, medicine in extracted_medicines.items():
                best_match, score, _ = process.extractOne(medicine, medicine_list, scorer=fuzz.ratio)

                if score >= threshold:
                    corrected_medicines[key] = best_match  # Replace incorrect name
                else:
                    corrected_medicines[key] = None  # No close match found

            return corrected_medicines

        # Run correction
        corrected = correct_medicines(extracted_medicines, medicine_list)

        return Response(corrected, status=status.HTTP_200_OK)