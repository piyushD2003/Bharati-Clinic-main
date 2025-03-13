from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from image_processing.models import PrescriptionRecord
from image_processing.filters import PrescriptionRecordFilter
from image_processing.serializers import PrescriptionSerializer
import google.generativeai as genai
import PIL.Image
import json
from datetime import datetime, timedelta
from django.core.paginator import Paginator


class ImageProcessingAPI(APIView):
    def post(self, request):
        Image = request.FILES.get("image")
        if not request.user.is_authenticated:
            return Response({"message": "Authentication credentials were not provided."},
                            status=status.HTTP_401_UNAUTHORIZED)

        if not Image:
            return Response({"error": "No image file provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            genai.configure(api_key="AIzaSyDV2EqHdJNBJ96S8279tQ1AhDF5roa4axg")
            model = genai.GenerativeModel("gemini-2.0-flash")
            organ = PIL.Image.open(Image)
            response = model.generate_content([
                '''Extract the following details from the given prescription image:

                    1. Patient Name: Extract the name of the patient mentioned.
                    2. Date: Extract the date in the format (YYYY-MM-DD).
                    3. Medications: For each medication, extract its name and dosage timing.
                        Guidelines for determining medication timing:
                        - The timing of the dosage is written after the medication name in the format (morning-afternoon-night), such as '1 -- (unrecognized character or symbol or anything) -- 1'. 
                        - Multiple variations are possible, including:
                        a. x-x-x / 1-x-x / x-1-x / x-x-1 / 1-1-x / 1-x-1 / x-1-1 
                        b. 1----------0---------1 / 0----------0---------1 / 0-----------1--------0 
                        c. x-----------x------------x / x----------x---------1 / x----------1-----------x / 1-----------x----------x 
                        or any variations thereof.
                        - Use these rules to determine the boolean values for timing:
                        - Any digit (e.g., 1, 1/2, 2) = true (indicates the medication is taken at this time).
                        - Any symbol (e.g., x, 0, >) = false (indicates the medication is not taken at this time).

                        Handle potential cursive handwriting where characters may appear connected or ambiguous. Preprocess the image to enhance clarity and separation of characters if necessary. Account for common misinterpretations where 'x' may look like '>', and ensure accurate interpretation based on context. Include potential variations like '1------x------1', '1--0--1', and other similar patterns to ensure robust handling of different styles. Utilize image processing techniques like binarization, noise removal, and character separation to improve the clarity and accuracy of the handwritten text extraction.

                    4. Place information will be given in right corner below the date, otherwise give blank ""
                    5. Weight value will be given in Weight field, otherwise give blank ""
                    6. B/P value always written below the B/P bold text, otherwise give blank ""
                    7. Age,Gender and Place given as Age/Gender/Place format example 52/F/jalgaon, 31/M/lucknow, etc, if value is missing give ""
                    8. Follow up date written in below most part of prescription otherwise give blank ""
                    9. All information must in english langauage
                    10. If field have no information dont give the null value, give the blank
                    Provide the result in this exact JSON format:
                    {
                        "patient_name": "Extracted Name",
                        "gender":"F(female) or M(male)",
                        "age":"extracted Age"
                        "weight":"Extracted Weight",
                        "bp":"Extracted B/P"
                        "place":"Extracted Place"
                        "prescription_date": "YYYY-MM-DD",
                        "follow_up_date":"YYYY-MM-DD",
                        "complaints":["Fever","cold",...],
                        "medications": [
                            {
                                "name": "Medication Name (dont take Tab)",
                                "timing": {
                                    "morning": true/false,
                                    "afternoon": true/false,
                                    "night": true/false
                                }
                            },
                            ...
                        ]
                    }
                    Ensure accuracy in interpreting the timing, handle potential cursive handwriting, and extract only the required details.

                ''', organ]) # noqa

            try:
                json_str = response.text.strip().strip('```json').strip('```').strip()
                json_data = json.loads(json_str)
                return Response(json_data, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"error": f"Json parsing error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"error": f"Generative ai error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PrescriptionAPI(APIView):
    def get(self, request):
        self.data = request.query_params
        self.pk = None

        if not request.user.is_authenticated:
            return Response({"message": "Authentication credentials were not provided."},
                            status=status.HTTP_401_UNAUTHORIZED)

        if "id" in self.data:
            self.pk = self.data.get("id")

        if "action" in self.data:
            action = str(self.data["action"])
            action_mapper = {
                "getPrescriptionRecord": self.getPrescriptionRecord,
                "getPrescriptionCount": self.getPrescriptionCount,
            }
            action_status = action_mapper.get(action)
            if action_status:
                action_status(request)
            else:
                return Response({"message": "Choose Wrong Option !", "data": None}, status.HTTP_400_BAD_REQUEST) # noqa
            return Response(self.ctx, self.status)
        else:
            return Response({"message": "Action is not in dict", "data": None}, status.HTTP_400_BAD_REQUEST) # noqa

    def getPrescriptionRecord(self, request):
        filterset_class = PrescriptionRecordFilter
        from_date = None
        to_date = None
        all_data = self.data.get("all_data", False)
        try:
            page_number = int(request.query_params.get("page", 1))  # Default page is 1
            records_number = int(request.query_params.get("records_number", 10))  # Default records per page is 10

            data = PrescriptionRecord.objects.all().order_by("-date_updated")

            # Filter by 'from_date' and 'to_date' if they exist in query params
            from_date = request.query_params.get("from_date")
            to_date = request.query_params.get("to_date")
            filter_response = request.query_params.get("filter_response")

            # Get today's date
            today = datetime.today().date()
            if filter_response == "today":
                from_date = today
                to_date = today  # Only today's records
                data = data.filter(prescription_date__range=[from_date, to_date])

            elif filter_response == "week":
                from_date = today - timedelta(days=today.weekday())  # Start of the current week (Monday)
                to_date = today  # Up to today
                data = data.filter(prescription_date__range=[from_date, to_date])

            elif filter_response == "month":
                from_date = today.replace(day=1)  # First day of the current month
                to_date = today  # Up to today
                data = data.filter(prescription_date__range=[from_date, to_date])

            elif from_date and to_date:
                try:
                    from_date = datetime.strptime(from_date, '%Y-%m-%d')
                    to_date = datetime.strptime(to_date, '%Y-%m-%d')
                    data = data.filter(prescription_date__range=[from_date, to_date])
                except ValueError:
                    return Response({"message": "Invalid date format. Use YYYY-MM-DD."},
                                    status=status.HTTP_400_BAD_REQUEST)

            elif from_date:
                try:
                    from_date = datetime.strptime(from_date, '%Y-%m-%d')
                    # Filter records for the specific date
                    data = data.filter(
                        prescription_date__gte=from_date,
                        prescription_date__lt=from_date
                    )
                except ValueError:
                    return Response({"message": "Invalid single_date format. Use YYYY-MM-DD."},
                                    status=status.HTTP_400_BAD_REQUEST)

            filtered_queryset = filterset_class(request.query_params, queryset=data).qs

            # calculating total records
            total_count = filtered_queryset.count()

            if all_data:
                serializer = PrescriptionSerializer(filtered_queryset, many=True).data
                self.ctx = {"message": "Successfully getting Prescription Record!", "data": serializer, "total_count": total_count}
                self.status = status.HTTP_200_OK
                return

            # Applying pagination
            paginator = Paginator(filtered_queryset, records_number)
            page_data = paginator.page(page_number)

            serializer = PrescriptionSerializer(page_data, many=True).data
            if self.pk and len(serializer):
                serializer = serializer[0]

            self.ctx = {"message": "Successfully getting Prescription Record!", "data": serializer, "total_count": total_count}
            self.status = status.HTTP_200_OK

        except Exception:
            self.ctx = {"message": "Error in fetching data!"}
            self.status = status.HTTP_404_NOT_FOUND
    

    def getPrescriptionCount(self, request):
        """ Get total prescription count with gender-wise breakdown. """
        try:
            # Get today's date as default
            filterset_class = PrescriptionRecordFilter
            from_date = request.query_params.get("from_date")
            to_date = request.query_params.get("to_date")
            today = datetime.today().date()

            if not from_date:
                from_date = today.strftime("%Y-%m-%d")
            if not to_date:
                to_date = today.strftime("%Y-%m-%d")


            try:
                from_date = datetime.strptime(from_date, "%Y-%m-%d").date()  # Convert to date
                to_date = datetime.strptime(to_date, "%Y-%m-%d").date()
            except ValueError:
                return Response({"message": "Invalid date format. Use YYYY-MM-DD."},
                                status=status.HTTP_400_BAD_REQUEST)

            # Get all prescription records within the date range
            data = PrescriptionRecord.objects.filter(prescription_date__range=[from_date, to_date])

            # Apply filters from filter.py
            filtered_queryset = filterset_class(request.query_params, queryset=data).qs
            # Calculate counts
            total_count = filtered_queryset.count()
            print(1,total_count)
            male_count = filtered_queryset.filter(gender="M").count()
            print(2,male_count)
            female_count = filtered_queryset.filter(gender="F").count()
            print(3)

            # Prepare response
            self.ctx = {
                "message": "Successfully retrieved prescription count!",
                "total_count": total_count,
                "Male": male_count,
                "Female": female_count,
            }
            self.status = status.HTTP_200_OK

        except Exception:
            self.ctx = {"message": "Error in fetching data!"}
            self.status = status.HTTP_500_INTERNAL_SERVER_ERROR

    def post(self, request):
        self.data = request.data

        if not request.user.is_authenticated:
            return Response({"message": "Authentication credentials were not provided."},
                            status=status.HTTP_401_UNAUTHORIZED)

        if "id" in self.data:
            self.pk = self.data.get("id")

        if "action" in self.data:
            action = str(self.data["action"])
            action_mapper = {
                "postPrescriptionRecord": self.postPrescriptionRecord,
                # "downloadExcel": self.downloadExcel,
                # Add more actions as needed
            }
            action_status = action_mapper.get(action)
            if action_status:
                action_status()
            else:
                return Response({"message": "Choose Wrong Option !", "data": None}, status.HTTP_400_BAD_REQUEST) # noqa
            return Response(self.ctx, self.status)
        else:
            return Response({"message": "Action is not in dict", "data": None}, status.HTTP_400_BAD_REQUEST) # noqa

    def postPrescriptionRecord(self):
        patient_name = self.data.get('patient_name')
        prescription_date = self.data.get('prescription_date')
        medications = self.data.get('medications')
        complaints = self.data.get('complaints', [])
        gender = self.data.get('gender', "")
        age = self.data.get('age', "")
        weight = self.data.get('weight', "")
        bp = self.data.get('bp', "")
        place = self.data.get('place', "")
        follow_up_date = self.data.get('follow_up_date')

        try:
            obj = PrescriptionRecord(
                patient_name=patient_name,
                prescription_date=prescription_date,
                medications=medications,
                complaints=complaints,
                gender=gender,
                age=age,
                weight=weight,
                bp=bp,
                place=place,
                follow_up_date=follow_up_date
            )

            obj.save()
            serializer = PrescriptionSerializer(obj).data
            self.ctx = {"message": "Prescription data is Created!", "data": serializer}
            self.status = status.HTTP_201_CREATED

        except Exception as e:
            self.ctx = {"message": "Something went wrong!", "error_msg": str(e)}
            self.status = status.HTTP_500_INTERNAL_SERVER_ERROR

    def patch(self, request):
        self.data = request.data

        if not request.user.is_authenticated:
            return Response({"message": "Authentication credentials were not provided."},
                            status=status.HTTP_401_UNAUTHORIZED)

        if "id" in self.data:
            self.id = self.data["id"]

        if "action" in self.data:
            action = str(self.data["action"])
            action_mapper = {
                "patchPrescriptionRecord": self.patchPrescriptionRecord
                # Add more actions as needed
            }
            action_status = action_mapper.get(action)
            if action_status:
                action_status()
            else:
                return Response({"message": "Choose Wrong Option !", "data": None}, status.HTTP_400_BAD_REQUEST) # noqa
            return Response(self.ctx, self.status)
        else:
            return Response({"message": "Action is not in dict", "data": None}, status.HTTP_400_BAD_REQUEST) # noqa

    def patchPrescriptionRecord(self):
        patient_name = self.data.get('patient_name')
        prescription_date = self.data.get('prescription_date')
        medications = self.data.get('medications')
        complaints = self.data.get('complaints')
        gender = self.data.get('gender')
        age = self.data.get('age')
        weight = self.data.get('weight')
        bp = self.data.get('bp')
        place = self.data.get('place')
        follow_up_date = self.data.get('follow_up_date')
        try:
            prescriptions = PrescriptionRecord.objects.filter(pk=self.id)
            if prescriptions.exists():
                prescriptions = prescriptions[0]
            else:
                self.ctx = {"message": f"users id {self.id} Not Found!"}
                self.status = status.HTTP_404_NOT_FOUND
                return
            if patient_name:
                prescriptions.patient_name = patient_name
            if prescription_date:
                prescriptions.prescription_date = prescription_date
            if medications:
                prescriptions.medications = medications
            if complaints:
                prescriptions.complaints = complaints
            if gender:
                prescriptions.gender = gender
            if age:
                prescriptions.age = age
            if weight:
                prescriptions.weight = weight
            if bp:
                prescriptions.bp = bp
            if place:
                prescriptions.place = place
            if follow_up_date:
                prescriptions.follow_up_date = follow_up_date

            prescriptions.save()
            serializer = PrescriptionSerializer(prescriptions).data
            self.ctx = {"message": "users is Updated!", "data": serializer}
            self.status = status.HTTP_201_CREATED

        except Exception as e:
            self.ctx = {"message": "Something went wrong!", "error_msg": str(e)}
            self.status = status.HTTP_500_INTERNAL_SERVER_ERROR

    def delete(self, request):
        self.data = request.data

        if not request.user.is_authenticated:
            return Response({"message": "Authentication credentials were not provided."},
                            status=status.HTTP_401_UNAUTHORIZED)

        if "id" in self.data:
            self.id = self.data["id"]

        if "action" in self.data:
            action = str(self.data["action"])
            action_mapper = {
                "delPrescriptionRecord": self.delPrescriptionRecord
            }

            action_status = action_mapper.get(action)
            if action_status:
                action_status()
            else:
                return Response({"message": "Choose Wrong Option !", "data": None}, status.HTTP_400_BAD_REQUEST) # noqa
            return Response(self.ctx, self.status)
        else:
            return Response({"message": "Action is not in dict", "data": None}, status.HTTP_400_BAD_REQUEST) # noqa

    def delPrescriptionRecord(self):
        try:
            data = PrescriptionRecord.objects.get(pk=self.id)
            if data:
                data.delete()
            self.ctx = {"message": "Prescription Record deleted!"}
            self.status = status.HTTP_201_CREATED
        except PrescriptionRecord.DoesNotExist:
            self.ctx = {"message": "Prescription Record id Not Found!"}
            self.status = status.HTTP_404_NOT_FOUND
        except Exception as e:
            self.ctx = {"message": "Something went wrong!", "error_msg": str(e)}
            self.status = status.HTTP_500_INTERNAL_SERVER_ERROR
