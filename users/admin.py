from django.contrib import admin
from users.models import User, DoctorPersonalDetail


admin.site.register(User)

admin.site.register(DoctorPersonalDetail)
