from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.auth.models import CarWash
from .models import WorkerProfile


def _resolve_request_tenant(request):
    user = getattr(request, 'user', None)
    tenant = getattr(user, 'tenant', None)
    if tenant is not None:
        return tenant
    fallback_tenant = CarWash.objects.order_by('id').first()
    if fallback_tenant and user and getattr(user, 'is_authenticated', False):
        user.tenant = fallback_tenant
        user.save(update_fields=['tenant'])
    return fallback_tenant


class WorkerProfileListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    phone = serializers.CharField(source='user.phone', read_only=True)
    payment_type = serializers.SerializerMethodField()
    payment_value = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return obj.user.full_name or obj.user.username

    def get_role(self, obj):
        return obj.user.get_role_display() if obj.user else ''

    def get_avatar(self, obj):
        name = self.get_full_name(obj).strip()
        if not name:
            return '---'
        parts = [part for part in name.split(' ') if part]
        if len(parts) >= 2:
            return f'{parts[0][0]}{parts[1][0]}'
        return name[:2]

    def get_payment_type(self, obj):
        if obj.payment_type:
            return obj.payment_type
        return 'fixed' if (obj.default_fixed_wage or 0) > 0 else 'percent'

    def get_payment_value(self, obj):
        if obj.payment_type == 'hourly':
            return obj.default_hourly_wage
        if obj.payment_type == 'fixed' or (obj.default_fixed_wage or 0) > 0:
            return obj.default_fixed_wage
        return obj.default_commission_percent

    class Meta:
        model = WorkerProfile
        fields = [
            'id',
            'full_name',
            'phone',
            'role',
            'avatar',
            'is_available',
            'load_status',
            'active_jobs_count',
            'payment_type',
            'payment_value',
            'tip_share_percent',
            'default_commission_percent',
            'default_fixed_wage',
            'default_hourly_wage',
            'last_assigned_at',
            'has_entrusted_item',
            'entrusted_item_description',
            'entrusted_item_quantity',
            'entrusted_item_price',
            'updated_at',
        ]


class WorkerProfileCreateUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=20)
    is_available = serializers.BooleanField(default=True)
    payment_type = serializers.ChoiceField(choices=['percent', 'fixed', 'hourly'], default='percent')
    payment_value = serializers.DecimalField(max_digits=12, decimal_places=2, default=0)
    tip_share_percent = serializers.DecimalField(max_digits=5, decimal_places=2, default=0)
    has_entrusted_item = serializers.BooleanField(default=False)
    entrusted_item_description = serializers.CharField(required=False, allow_blank=True)
    entrusted_item_quantity = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0)
    entrusted_item_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)

    def validate_full_name(self, value):
        value = str(value or '').strip()
        if not value:
            raise serializers.ValidationError('نام پرسنل الزامی است.')
        return value

    def validate_phone(self, value):
        request = self.context.get('request')
        tenant = _resolve_request_tenant(request) if request else None
        value = str(value or '').strip()
        if not value:
            raise serializers.ValidationError('شماره موبایل الزامی است.')

        user_model = get_user_model()
        existing_user = user_model.objects.filter(phone=value).first()
        instance = getattr(self, 'instance', None)
        if instance and getattr(instance, 'user_id', None) == getattr(existing_user, 'id', None):
            return value

        if existing_user and existing_user.tenant_id != getattr(tenant, 'id', None):
            raise serializers.ValidationError('این شماره موبایل قبلا در یک کارواش دیگر ثبت شده است.')
        return value

    def validate(self, attrs):
        payment_type = attrs.get('payment_type', 'percent')
        payment_value = attrs.get('payment_value', 0) or 0
        if payment_value < 0:
            raise serializers.ValidationError({'payment_value': 'مقدار پرداخت نمی‌تواند منفی باشد.'})
        if payment_type == 'percent' and payment_value > 100:
            raise serializers.ValidationError({'payment_value': 'درصد پرداخت باید بین ۰ تا ۱۰۰ باشد.'})
        tip_share_percent = attrs.get('tip_share_percent', 0) or 0
        if tip_share_percent < 0 or tip_share_percent > 100:
            raise serializers.ValidationError({'tip_share_percent': 'درصد انعام باید بین ۰ تا ۱۰۰ باشد.'})
        has_entrusted_item = bool(attrs.get('has_entrusted_item', False))
        entrusted_item_quantity = attrs.get('entrusted_item_quantity', 0) or 0
        entrusted_item_price = attrs.get('entrusted_item_price', 0) or 0
        entrusted_item_description = str(attrs.get('entrusted_item_description', '') or '').strip()
        if has_entrusted_item and not entrusted_item_description:
            raise serializers.ValidationError({'entrusted_item_description': 'شرح امانت الزامی است.'})
        if entrusted_item_quantity < 0:
            raise serializers.ValidationError({'entrusted_item_quantity': 'تعداد امانت نمی‌تواند منفی باشد.'})
        if entrusted_item_price < 0:
            raise serializers.ValidationError({'entrusted_item_price': 'قیمت امانت نمی‌تواند منفی باشد.'})
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        tenant = _resolve_request_tenant(request) if request else None
        if tenant is None:
            raise serializers.ValidationError({'detail': 'کارواش کاربر مشخص نیست.'})

        user_model = get_user_model()
        phone = validated_data['phone']
        full_name = validated_data['full_name']
        user = user_model.objects.filter(phone=phone, tenant=tenant).first()
        if not user:
            username = phone
            base = username
            counter = 1
            while user_model.objects.filter(username__iexact=username).exists():
                counter += 1
                username = f'{base}_{counter}'
            user = user_model.objects.create(
                username=username,
                full_name=full_name,
                phone=phone,
                tenant=tenant,
                role='worker',
                is_active=True,
            )
            user.set_password('Worker@12345')
            user.save()
        else:
            user.full_name = full_name
            if user.role != 'worker':
                user.role = 'worker'
            user.save(update_fields=['full_name', 'role'])

        profile, _ = WorkerProfile.objects.get_or_create(user=user, defaults={'tenant': tenant})
        if profile.tenant_id is None:
            profile.tenant = tenant
        profile.is_available = validated_data.get('is_available', True)
        profile.has_entrusted_item = bool(validated_data.get('has_entrusted_item', False))
        profile.entrusted_item_description = (validated_data.get('entrusted_item_description') or '').strip()
        profile.entrusted_item_quantity = validated_data.get('entrusted_item_quantity', 0) or 0
        profile.entrusted_item_price = validated_data.get('entrusted_item_price', 0) or 0
        payment_type = validated_data.get('payment_type', 'percent')
        payment_value = validated_data.get('payment_value', 0) or 0
        profile.tip_share_percent = validated_data.get('tip_share_percent', 0) or 0
        if payment_type == 'fixed':
            profile.default_fixed_wage = payment_value
            profile.default_hourly_wage = 0
            profile.default_commission_percent = 0
            profile.payment_type = 'fixed'
        elif payment_type == 'hourly':
            profile.default_hourly_wage = payment_value
            profile.default_fixed_wage = 0
            profile.default_commission_percent = 0
            profile.payment_type = 'hourly'
        else:
            profile.default_commission_percent = payment_value
            profile.default_fixed_wage = 0
            profile.default_hourly_wage = 0
            profile.payment_type = 'percent'
        profile.save(update_fields=['tenant', 'is_available', 'default_commission_percent', 'default_fixed_wage', 'default_hourly_wage', 'payment_type', 'tip_share_percent', 'has_entrusted_item', 'entrusted_item_description', 'entrusted_item_quantity', 'entrusted_item_price', 'updated_at'])

        return profile

    def update(self, instance, validated_data):
        next_phone = validated_data.get('phone', instance.user.phone)
        if get_user_model().objects.exclude(id=instance.user_id).filter(phone=next_phone).exists():
            raise serializers.ValidationError({'phone': 'این شماره موبایل قبلا ثبت شده است.'})
        instance.user.full_name = validated_data.get('full_name', instance.user.full_name)
        instance.user.phone = next_phone
        instance.user.save(update_fields=['full_name', 'phone'])
        instance.is_available = validated_data.get('is_available', instance.is_available)
        instance.has_entrusted_item = bool(validated_data.get('has_entrusted_item', instance.has_entrusted_item))
        instance.entrusted_item_description = (validated_data.get('entrusted_item_description', instance.entrusted_item_description) or '').strip()
        instance.entrusted_item_quantity = validated_data.get('entrusted_item_quantity', instance.entrusted_item_quantity) or 0
        instance.entrusted_item_price = validated_data.get('entrusted_item_price', instance.entrusted_item_price) or 0
        payment_type = validated_data.get('payment_type', 'percent')
        payment_value = validated_data.get('payment_value', 0) or 0
        instance.tip_share_percent = validated_data.get('tip_share_percent', 0) or 0
        if payment_type == 'fixed':
            instance.default_fixed_wage = payment_value
            instance.default_hourly_wage = 0
            instance.default_commission_percent = 0
            instance.payment_type = 'fixed'
        elif payment_type == 'hourly':
            instance.default_hourly_wage = payment_value
            instance.default_fixed_wage = 0
            instance.default_commission_percent = 0
            instance.payment_type = 'hourly'
        else:
            instance.default_commission_percent = payment_value
            instance.default_fixed_wage = 0
            instance.default_hourly_wage = 0
            instance.payment_type = 'percent'
        instance.save(update_fields=['is_available', 'default_commission_percent', 'default_fixed_wage', 'default_hourly_wage', 'payment_type', 'tip_share_percent', 'has_entrusted_item', 'entrusted_item_description', 'entrusted_item_quantity', 'entrusted_item_price', 'updated_at'])

        return instance
