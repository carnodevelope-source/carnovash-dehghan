from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import WorkerProfile


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
        return 'fixed' if (obj.default_fixed_wage or 0) > 0 else 'percent'

    def get_payment_value(self, obj):
        if (obj.default_fixed_wage or 0) > 0:
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
        ]


class WorkerProfileCreateUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=20)
    is_available = serializers.BooleanField(default=True)
    payment_type = serializers.ChoiceField(choices=['percent', 'fixed'], default='percent')
    payment_value = serializers.DecimalField(max_digits=12, decimal_places=2, default=0)
    tip_share_percent = serializers.DecimalField(max_digits=5, decimal_places=2, default=0)

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
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        tenant = getattr(getattr(request, 'user', None), 'tenant', None)
        if tenant is None:
            raise serializers.ValidationError({'detail': 'Tenant is required.'})

        user_model = get_user_model()
        phone = validated_data['phone']
        full_name = validated_data['full_name']
        user = user_model.objects.filter(phone=phone, tenant=tenant).first()
        if not user:
            username = phone
            base = username
            counter = 1
            while user_model.objects.filter(username=username).exists():
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
        payment_type = validated_data.get('payment_type', 'percent')
        payment_value = validated_data.get('payment_value', 0) or 0
        profile.tip_share_percent = validated_data.get('tip_share_percent', 0) or 0
        if payment_type == 'fixed':
            profile.default_fixed_wage = payment_value
            profile.default_commission_percent = 0
        else:
            profile.default_commission_percent = payment_value
            profile.default_fixed_wage = 0
        profile.save(update_fields=['tenant', 'is_available', 'default_commission_percent', 'default_fixed_wage', 'tip_share_percent', 'updated_at'])

        return profile

    def update(self, instance, validated_data):
        instance.user.full_name = validated_data.get('full_name', instance.user.full_name)
        instance.user.phone = validated_data.get('phone', instance.user.phone)
        instance.user.save(update_fields=['full_name', 'phone'])
        instance.is_available = validated_data.get('is_available', instance.is_available)
        payment_type = validated_data.get('payment_type', 'percent')
        payment_value = validated_data.get('payment_value', 0) or 0
        instance.tip_share_percent = validated_data.get('tip_share_percent', 0) or 0
        if payment_type == 'fixed':
            instance.default_fixed_wage = payment_value
            instance.default_commission_percent = 0
        else:
            instance.default_commission_percent = payment_value
            instance.default_fixed_wage = 0
        instance.save(update_fields=['is_available', 'default_commission_percent', 'default_fixed_wage', 'tip_share_percent', 'updated_at'])

        return instance
