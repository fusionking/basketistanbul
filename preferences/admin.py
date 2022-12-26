from django.contrib import admin

from preferences.models import Preference, SelectionPreference

# Register your models here.
admin.site.register(Preference)
admin.site.register(SelectionPreference)
