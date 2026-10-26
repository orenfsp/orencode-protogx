from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Guardian, PersonalDataConsent, User, UserRole


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "full_name", "is_staff")
    fieldsets = ((None, {"fields": ("email", "password")}), ("Personal", {"fields": ("full_name", "date_of_birth")}), ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}))
    add_fieldsets = ((None, {"fields": ("email", "full_name", "password1", "password2")}),)
    search_fields = ("email", "full_name")


admin.site.register(UserRole)
admin.site.register(Guardian)
admin.site.register(PersonalDataConsent)
