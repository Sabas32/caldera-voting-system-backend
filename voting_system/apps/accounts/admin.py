from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from voting_system.apps.accounts.models import OrgMembership, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("email", "is_system_admin", "is_staff", "is_active")
    list_filter = ("is_system_admin", "is_staff", "is_active")
    ordering = ("email",)
    search_fields = ("email", "first_name", "last_name")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_system_admin", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login",)}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_system_admin", "is_staff", "is_active"),
            },
        ),
    )


@admin.register(OrgMembership)
class OrgMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "role", "is_active", "created_at")
    list_filter = ("role", "is_active", "organization")
    search_fields = ("user__email", "organization__name", "organization__slug")
