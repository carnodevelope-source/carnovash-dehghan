from rest_framework import serializers

from .models import (
    BulkServiceJob,
    PlatformProject,
    ServiceAlert,
    ServiceAuditLog,
    ServiceOrder,
    ServicePaymentRecord,
    ServicePeriod,
    ServicePlan,
    ServiceProduct,
    ServiceSubscription,
)


class PlatformProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformProject
        fields = ['id', 'code', 'name', 'is_active', 'sort_order']


class ServicePlanSerializer(serializers.ModelSerializer):
    computed = serializers.SerializerMethodField()

    class Meta:
        model = ServicePlan
        fields = [
            'id', 'code', 'title', 'billing_cycle', 'duration_days', 'base_price', 'discount_percent',
            'tax_percent', 'usage_cap', 'usage_unit', 'enabled_features_json', 'disabled_features_json',
            'renewal_terms', 'installment_months', 'upfront_amount', 'monthly_installment_amount',
            'is_active', 'sort_order', 'computed',
        ]

    def get_computed(self, obj):
        amounts = obj.compute_amounts()
        return {key: float(value) for key, value in amounts.items()}


class ServiceProductSerializer(serializers.ModelSerializer):
    plans = ServicePlanSerializer(many=True, read_only=True)
    project_code = serializers.CharField(source='project.code', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)

    class Meta:
        model = ServiceProduct
        fields = [
            'id', 'project', 'project_code', 'project_name', 'product_key', 'feature_key', 'title',
            'subtitle', 'description', 'features_json', 'limits_json', 'is_available', 'is_required',
            'sort_order', 'default_cost', 'tax_percent', 'grace_days_default', 'reminder_days_json',
            'accent', 'plans',
        ]


class ServiceSubscriptionSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='tenant.name', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    project_code = serializers.CharField(source='project.code', read_only=True)
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_key = serializers.CharField(source='product.product_key', read_only=True)
    plan_title = serializers.CharField(source='plan.title', read_only=True, default='')
    plan_code = serializers.CharField(source='plan.code', read_only=True, default='')
    days_remaining = serializers.SerializerMethodField()
    usage_percent = serializers.SerializerMethodField()
    sales_owner_name = serializers.SerializerMethodField()
    support_owner_name = serializers.SerializerMethodField()

    class Meta:
        model = ServiceSubscription
        fields = [
            'id', 'tenant', 'client_name', 'project', 'project_name', 'project_code', 'product',
            'product_title', 'product_key', 'plan', 'plan_title', 'plan_code', 'status', 'payment_status',
            'auto_renew', 'purchased_at', 'activated_at', 'starts_at', 'ends_at', 'grace_ends_at',
            'last_renewed_at', 'last_paid_at', 'last_activity_at', 'base_amount', 'discount_amount',
            'tax_amount', 'final_amount', 'paid_amount', 'remaining_amount', 'cost_amount', 'usage_cap',
            'usage_used', 'usage_unit', 'usage_percent', 'days_remaining', 'license_code', 'seat_limit',
            'device_limit', 'sales_owner', 'sales_owner_name', 'support_owner', 'support_owner_name',
            'contract_number', 'meta', 'created_at', 'updated_at',
        ]

    def get_days_remaining(self, obj):
        return obj.days_remaining

    def get_usage_percent(self, obj):
        return float(obj.usage_percent or 0)

    def get_sales_owner_name(self, obj):
        user = obj.sales_owner
        return (user.full_name or user.username) if user else ''

    def get_support_owner_name(self, obj):
        user = obj.support_owner
        return (user.full_name or user.username) if user else ''


class ServiceOrderSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    plan_title = serializers.CharField(source='plan.title', read_only=True, default='')
    client_name = serializers.CharField(source='tenant.name', read_only=True)

    class Meta:
        model = ServiceOrder
        fields = [
            'id', 'order_code', 'tenant', 'client_name', 'project', 'product', 'product_title', 'plan',
            'plan_title', 'subscription', 'status', 'payment_method', 'base_amount', 'discount_amount',
            'tax_amount', 'final_amount', 'paid_amount', 'remaining_amount', 'tracking_code',
            'approved_by', 'approved_at', 'paid_at', 'activated_at', 'created_at', 'meta',
        ]


class ServicePeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServicePeriod
        fields = [
            'id', 'kind', 'starts_at', 'ends_at', 'base_amount', 'discount_amount', 'tax_amount',
            'final_amount', 'paid_amount', 'cost_amount', 'note', 'created_at',
        ]


class ServicePaymentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServicePaymentRecord
        fields = [
            'id', 'kind', 'amount', 'tax_amount', 'discount_amount', 'method', 'tracking_code',
            'paid_at', 'note', 'created_at',
        ]


class ServiceAuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = ServiceAuditLog
        fields = [
            'id', 'action', 'reason', 'note', 'before_status', 'after_status', 'financial_impact',
            'access_impact', 'actor', 'actor_name', 'payload', 'created_at',
        ]

    def get_actor_name(self, obj):
        user = obj.actor
        return (user.full_name or user.username) if user else ''


class ServiceAlertSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='tenant.name', read_only=True)
    product_title = serializers.CharField(source='subscription.product.title', read_only=True, default='')

    class Meta:
        model = ServiceAlert
        fields = [
            'id', 'tenant', 'client_name', 'subscription', 'product_title', 'code', 'title', 'message',
            'severity', 'is_resolved', 'created_at', 'resolved_at',
        ]


class BulkServiceJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = BulkServiceJob
        fields = [
            'id', 'action', 'status', 'payload', 'success_count', 'failure_count',
            'started_at', 'finished_at', 'created_at',
        ]
