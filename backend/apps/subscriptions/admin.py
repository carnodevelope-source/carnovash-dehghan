from django.contrib import admin

from . import models


@admin.register(models.PlatformProject)
class PlatformProjectAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_active', 'sort_order')
    search_fields = ('code', 'name')


class ServicePlanInline(admin.TabularInline):
    model = models.ServicePlan
    extra = 0


@admin.register(models.ServiceProduct)
class ServiceProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'product_key', 'feature_key', 'is_available', 'is_required', 'sort_order')
    list_filter = ('project', 'product_key', 'is_available')
    search_fields = ('title', 'product_key', 'feature_key')
    inlines = [ServicePlanInline]


@admin.register(models.ServiceSubscription)
class ServiceSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'product', 'status', 'payment_status', 'final_amount', 'remaining_amount', 'ends_at')
    list_filter = ('status', 'payment_status', 'product__product_key', 'project')
    search_fields = ('tenant__name', 'license_code', 'contract_number')
    raw_id_fields = ('tenant', 'product', 'plan', 'feature_purchase', 'sales_owner', 'support_owner')


@admin.register(models.ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):
    list_display = ('order_code', 'tenant', 'product', 'status', 'final_amount', 'paid_amount', 'created_at')
    list_filter = ('status', 'payment_method')
    search_fields = ('order_code', 'tracking_code', 'tenant__name')


@admin.register(models.ServicePeriod)
class ServicePeriodAdmin(admin.ModelAdmin):
    list_display = ('subscription', 'kind', 'starts_at', 'ends_at', 'final_amount', 'paid_amount')
    list_filter = ('kind',)


@admin.register(models.ServicePaymentRecord)
class ServicePaymentRecordAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'kind', 'amount', 'method', 'tracking_code', 'paid_at')
    list_filter = ('kind', 'method')


@admin.register(models.ServiceAuditLog)
class ServiceAuditLogAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'action', 'before_status', 'after_status', 'actor', 'created_at')
    list_filter = ('action',)
    search_fields = ('tenant__name', 'reason', 'note')


@admin.register(models.ServiceAlert)
class ServiceAlertAdmin(admin.ModelAdmin):
    list_display = ('title', 'tenant', 'severity', 'is_resolved', 'created_at')
    list_filter = ('severity', 'is_resolved', 'code')


@admin.register(models.BulkServiceJob)
class BulkServiceJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'action', 'status', 'success_count', 'failure_count', 'created_at')
    list_filter = ('action', 'status')
