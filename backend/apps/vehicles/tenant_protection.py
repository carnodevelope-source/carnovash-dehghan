from django.core.exceptions import ValidationError
from django.db import models


ERROR = 'Customer and vehicle ownership is inconsistent.'


class TenantProtectedQuerySet(models.QuerySet):
    def update(self, **kwargs):
        protected = {'tenant', 'tenant_id'}
        if self.model._meta.model_name == 'vehicleentry':
            protected |= {'customer', 'customer_id'}
        if protected.intersection(kwargs):
            raise ValidationError(ERROR)
        return super().update(**kwargs)

    def bulk_create(self, objs, *args, **kwargs):
        objs = list(objs)
        if kwargs.get('update_conflicts') or (len(args) > 2 and args[2]):
            raise ValidationError(ERROR)
        from django.db import transaction
        with transaction.atomic(using=self.db):
            for obj in objs:
                obj.validate_tenant_link(using=self.db)
            return super().bulk_create(objs, *args, **kwargs)

    def bulk_update(self, objs, fields, **kwargs):
        if {'tenant', 'tenant_id', 'customer', 'customer_id'}.intersection(fields):
            raise ValidationError(ERROR)
        return super().bulk_update(objs, fields, **kwargs)
