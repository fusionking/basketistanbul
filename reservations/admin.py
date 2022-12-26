from django.contrib import admin

from reservations.models import Reservation, ReservationJob

# Register your models here.
admin.site.register(Reservation)
admin.site.register(ReservationJob)
