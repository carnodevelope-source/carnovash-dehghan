from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            'CarWash',
            {
                'fields': ('full_name', 'phone', 'role', 'is_active_worker'),
            },
        ),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        (
            'CarWash',
            {
                'fields': ('full_name', 'phone', 'role', 'is_active_worker'),
            },
        ),
    )
    list_display = ('id', 'username', 'full_name', 'phone', 'role', 'is_staff', 'is_active')
    search_fields = ('username', 'full_name', 'phone')
