from django.core.exceptions import ValidationError
from django.db import models, router, transaction


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
        with transaction.atomic(using=self.db):
            for obj in objs:
                obj.validate_tenant_link(using=self.db, lock=True)
            return super().bulk_create(objs, *args, **kwargs)

    def bulk_update(self, objs, fields, **kwargs):
        if {'tenant', 'tenant_id', 'customer', 'customer_id'}.intersection(fields):
            raise ValidationError(ERROR)
        return super().bulk_update(objs, fields, **kwargs)


class TenantOwnershipMixin:
    """Validate and lock in the same transaction as ordinary instance writes.

    Calling Model.save_base explicitly, SQL and independently constructed
    QuerySets are deliberate bypasses; this does not claim a DB constraint.
    """
    def save_base(self, raw=False, force_insert=False, force_update=False,
                  using=None, update_fields=None):
        using = using or router.db_for_write(type(self), instance=self)
        with transaction.atomic(using=using):
            self.validate_tenant_link(using=using, lock=True, update_fields=update_fields)
            return super().save_base(raw=raw, force_insert=force_insert,
                                     force_update=force_update, using=using,
                                     update_fields=update_fields)
