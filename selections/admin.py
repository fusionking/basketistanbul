from django.contrib import admin

from selections.models import Selection, Slot, SportSelection

# Register your models here.


class SportSelectionAdmin(admin.ModelAdmin):
    list_display = ("branch_name", "complex_name", "pitch_name")
    fields = ()
    readonly_fields = ("branch_id", "complex_id", "pitch_id")


admin.site.register(SportSelection, SportSelectionAdmin)
admin.site.register(Slot)
admin.site.register(Selection)
