from django.contrib import admin
from django.contrib.auth import get_user_model


# Register your models here.
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "tckn",
    )
    fields = (
        "email",
        "tckn",
        "phone_number",
        "is_active",
        "is_staff",
        "first_name",
        "last_name",
        "groups",
        "is_superuser",
    )


admin.site.register(get_user_model(), UserAdmin)
