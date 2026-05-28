from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        OWNER = 'owner', 'Owner'
        MANAGER = 'manager', 'Manager'
        ACCOUNTANT = 'accountant', 'Accountant'
        OPERATOR = 'operator', 'Operator'
        WORKER = 'worker', 'Worker'

    full_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, unique=True)
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.OPERATOR)
    is_active_worker = models.BooleanField(default=True)

    REQUIRED_FIELDS = ['email', 'phone']

    def __str__(self) -> str:
        return self.username
