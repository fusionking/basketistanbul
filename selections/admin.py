from django.contrib import admin

from selections.models import SportSelection, Slot, Selection

# Register your models here.
admin.site.register(SportSelection)
admin.site.register(Slot)
admin.site.register(Selection)
