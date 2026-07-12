from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
import secrets

from apps.auth.models import CarWash
from .models import WorkerAttendance, WorkerProfile


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


def ensure_attendance_token(profile):
    if not profile.attendance_token:
        profile.attendance_token = secrets.token_urlsafe(24)
        profile.save(update_fields=['attendance_token', 'updated_at'])
    return profile.attendance_token


def _generate_worker_username(user_model, phone=''):
    digits = ''.join(ch for ch in str(phone or '') if ch.isdigit())
    base = f"worker-{digits[-4:]}" if digits else 'worker'
    candidate = base
    suffix = 1
    while user_model.objects.filter(username__iexact=candidate).exists():
        suffix += 1
        candidate = f'{base}-{suffix}'
    return candidate


class WorkerProfileListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    role_key = serializers.CharField(source='user.role', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    avatar = serializers.SerializerMethodField()
    phone = serializers.CharField(source='user.phone', read_only=True)
    started_at = serializers.DateField(read_only=True)
    address = serializers.CharField(read_only=True)
    payment_type = serializers.SerializerMethodField()
    payment_value = serializers.SerializerMethodField()
    insurance_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    entrusted_items = serializers.SerializerMethodField()
    attendance_token = serializers.SerializerMethodField()
    attendance_path = serializers.SerializerMethodField()
    current_status = serializers.SerializerMethodField()
    last_event_at = serializers.SerializerMethodField()
    open_shift_started_at = serializers.SerializerMethodField()
    queue_position_at = serializers.SerializerMethodField()

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

    def get_entrusted_items(self, obj):
        raw_items = obj.entrusted_items if isinstance(obj.entrusted_items, list) else []
        if raw_items:
            return raw_items
        if obj.has_entrusted_item and str(obj.entrusted_item_description or '').strip():
            return [{
                'title': str(obj.entrusted_item_description or '').strip(),
                'quantity': float(obj.entrusted_item_quantity or 0),
                'price': float(obj.entrusted_item_price or 0),
            }]
        return []

    def get_attendance_token(self, obj):
        return ensure_attendance_token(obj)

    def get_attendance_path(self, obj):
        token = ensure_attendance_token(obj)
        return f'/attendance/{token}'

    def _attendance_queue_state(self, obj):
        state = getattr(obj, '_attendance_queue_state', None)
        return state if isinstance(state, dict) else {}

    def get_current_status(self, obj):
        return self._attendance_queue_state(obj).get('current_status', 'out')

    def get_last_event_at(self, obj):
        return self._attendance_queue_state(obj).get('last_event_at')

    def get_open_shift_started_at(self, obj):
        return self._attendance_queue_state(obj).get('open_shift_started_at')

    def get_queue_position_at(self, obj):
        return self._attendance_queue_state(obj).get('queue_position_at')

    class Meta:
        model = WorkerProfile
        fields = [
            'id',
            'full_name',
            'username',
            'phone',
            'started_at',
            'address',
            'role',
            'role_key',
            'avatar',
            'is_available',
            'load_status',
            'active_jobs_count',
            'payment_type',
            'payment_value',
            'insurance_amount',
            'tip_share_percent',
            'default_commission_percent',
            'default_fixed_wage',
            'default_hourly_wage',
            'last_assigned_at',
            'has_entrusted_item',
            'entrusted_items',
            'entrusted_item_description',
            'entrusted_item_quantity',
            'entrusted_item_price',
            'attendance_token',
            'attendance_path',
            'current_status',
            'last_event_at',
            'open_shift_started_at',
            'queue_position_at',
            'updated_at',
        ]


class WorkerAttendanceEventSerializer(serializers.ModelSerializer):
    worker_name = serializers.SerializerMethodField()
    worker_avatar = serializers.SerializerMethodField()

    def get_worker_name(self, obj):
        if not obj.worker or not obj.worker.user:
            return '-'
        return obj.worker.user.full_name or obj.worker.user.username or '-'

    def get_worker_avatar(self, obj):
        if not obj.worker or not obj.worker.user:
            return '--'
        name = obj.worker.user.full_name or obj.worker.user.username or ''
        parts = [part for part in name.split(' ') if part]
        if len(parts) >= 2:
            return f'{parts[0][0]}{parts[1][0]}'
        return name[:2] or '--'

    class Meta:
        model = WorkerAttendance
        fields = [
            'id',
            'worker',
            'worker_name',
            'worker_avatar',
            'event_type',
            'event_at',
            'source',
            'note',
        ]


class WorkerProfileCreateUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    username = serializers.CharField(max_length=150, required=False, allow_blank=True)
    password = serializers.CharField(max_length=128, required=False, allow_blank=True, write_only=True)
    phone = serializers.CharField(max_length=20)
    role = serializers.ChoiceField(choices=['operator', 'worker'], default='worker')
    started_at = serializers.DateField(required=False, allow_null=True)
    address = serializers.CharField(required=False, allow_blank=True)
    is_available = serializers.BooleanField(default=True)
    payment_type = serializers.ChoiceField(choices=['percent', 'fixed', 'hourly'], default='percent')
    payment_value = serializers.DecimalField(max_digits=12, decimal_places=2, default=0)
    insurance_amount = serializers.DecimalField(max_digits=12, decimal_places=2, default=0)
    tip_share_percent = serializers.DecimalField(max_digits=5, decimal_places=2, default=0)
    has_entrusted_item = serializers.BooleanField(default=False)
    entrusted_items = serializers.ListField(child=serializers.DictField(), required=False, default=list)
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

        if existing_user:
            if existing_user.tenant_id == getattr(tenant, 'id', None):
                raise serializers.ValidationError('این شماره موبایل قبلا ثبت شده است.')
            raise serializers.ValidationError('این شماره موبایل قبلا در یک کارواش دیگر ثبت شده است.')
        return value

    def validate_username(self, value):
        value = str(value or '').strip()
        if not value:
            role = str(self.initial_data.get('role') or 'worker').strip().lower()
            if role == 'worker':
                return ''
            raise serializers.ValidationError('نام کاربری الزامی است.')
        user_model = get_user_model()
        instance = getattr(self, 'instance', None)
        existing_user = user_model.objects.filter(username__iexact=value).first()
        if instance and getattr(instance, 'user_id', None) == getattr(existing_user, 'id', None):
            return value
        if existing_user:
            raise serializers.ValidationError('این نام کاربری قبلا ثبت شده است.')
        return value

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)
        password = str(attrs.get('password') or '')
        role = str(attrs.get('role') or self.initial_data.get('role') or 'worker').strip().lower()
        if instance is None and role != 'worker' and not password.strip():
            raise serializers.ValidationError({'password': 'رمز عبور برای پرسنل جدید الزامی است.'})
        payment_type = attrs.get('payment_type', 'percent')
        payment_value = attrs.get('payment_value', 0) or 0
        if payment_value < 0:
            raise serializers.ValidationError({'payment_value': 'مقدار پرداخت نمی‌تواند منفی باشد.'})
        if payment_type == 'percent' and payment_value > 100:
            raise serializers.ValidationError({'payment_value': 'درصد پرداخت باید بین ۰ تا ۱۰۰ باشد.'})
        insurance_amount = attrs.get('insurance_amount', 0) or 0
        if insurance_amount < 0:
            raise serializers.ValidationError({'insurance_amount': 'مبلغ حق بیمه نمی‌تواند منفی باشد.'})
        tip_share_percent = attrs.get('tip_share_percent', 0) or 0
        if tip_share_percent < 0 or tip_share_percent > 100:
            raise serializers.ValidationError({'tip_share_percent': 'درصد انعام باید بین ۰ تا ۱۰۰ باشد.'})
        has_entrusted_item = bool(attrs.get('has_entrusted_item', False))
        entrusted_items = attrs.get('entrusted_items', []) or []
        normalized_items = []
        for index, item in enumerate(entrusted_items):
            title = str(item.get('title') or item.get('description') or '').strip()
            entrusted_at = str(item.get('entrusted_at') or item.get('date') or '').strip()
            quantity = item.get('quantity', 0) or 0
            price = item.get('price', 0) or 0
            try:
                quantity = float(quantity)
                price = float(price)
            except (TypeError, ValueError):
                raise serializers.ValidationError({'entrusted_items': f'اطلاعات ردیف {index + 1} نامعتبر است.'})
            if not title and quantity <= 0 and price <= 0:
                continue
            if not title:
                raise serializers.ValidationError({'entrusted_items': f'شرح ردیف {index + 1} الزامی است.'})
            if quantity < 0:
                raise serializers.ValidationError({'entrusted_items': f'تعداد ردیف {index + 1} نمی‌تواند منفی باشد.'})
            if price < 0:
                raise serializers.ValidationError({'entrusted_items': f'قیمت ردیف {index + 1} نمی‌تواند منفی باشد.'})
            normalized_items.append({
                'title': title,
                'entrusted_at': entrusted_at,
                'quantity': quantity,
                'price': price,
            })
        if has_entrusted_item and not normalized_items:
            entrusted_item_description = str(attrs.get('entrusted_item_description', '') or '').strip()
            entrusted_item_quantity = attrs.get('entrusted_item_quantity', 0) or 0
            entrusted_item_price = attrs.get('entrusted_item_price', 0) or 0
            if entrusted_item_description:
                normalized_items.append({
                    'title': entrusted_item_description,
                    'quantity': float(entrusted_item_quantity),
                    'price': float(entrusted_item_price),
                })
        attrs['entrusted_items'] = normalized_items
        attrs['has_entrusted_item'] = bool(normalized_items) if has_entrusted_item else False
        if normalized_items:
            attrs['entrusted_item_description'] = normalized_items[0]['title']
            attrs['entrusted_item_quantity'] = normalized_items[0]['quantity']
            attrs['entrusted_item_price'] = normalized_items[0]['price']
        else:
            attrs['entrusted_item_description'] = ''
            attrs['entrusted_item_quantity'] = 0
            attrs['entrusted_item_price'] = 0
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        tenant = _resolve_request_tenant(request) if request else None
        if tenant is None:
            raise serializers.ValidationError({'detail': 'کارواش کاربر مشخص نیست.'})

        user_model = get_user_model()
        phone = validated_data['phone']
        full_name = validated_data['full_name']
        role = validated_data.get('role', 'worker')
        username = str(validated_data.get('username') or '').strip()
        if not username:
            username = _generate_worker_username(user_model, phone=phone)
        password = str(validated_data.get('password') or '').strip()
        generated_password = False
        if not password and role == 'worker':
            password = secrets.token_urlsafe(10)
            generated_password = True
        self.created_credentials = None
        is_available = validated_data.get('is_available', True)
        user = user_model.objects.create(
            username=username,
            full_name=full_name,
            phone=phone,
            tenant=tenant,
            role=role,
            is_active=is_available,
        )
        user.set_password(password)
        user.save()
        if password and not generated_password:
            self.created_credentials = {
                'tenant': tenant,
                'phone': phone,
                'username': username,
                'password': password,
                'role': role,
            }

        profile, _ = WorkerProfile.objects.get_or_create(user=user, defaults={'tenant': tenant})
        if profile.tenant_id is None:
            profile.tenant = tenant
        profile.is_available = validated_data.get('is_available', True)
        joined_at = timezone.localtime(user.date_joined) if timezone.is_aware(user.date_joined) else user.date_joined
        profile.started_at = joined_at.date()
        profile.address = str(validated_data.get('address') or '').strip()
        profile.has_entrusted_item = bool(validated_data.get('has_entrusted_item', False))
        profile.entrusted_items = validated_data.get('entrusted_items', [])
        profile.entrusted_item_description = (validated_data.get('entrusted_item_description') or '').strip()
        profile.entrusted_item_quantity = validated_data.get('entrusted_item_quantity', 0) or 0
        profile.entrusted_item_price = validated_data.get('entrusted_item_price', 0) or 0
        payment_type = validated_data.get('payment_type', 'percent')
        payment_value = validated_data.get('payment_value', 0) or 0
        profile.tip_share_percent = validated_data.get('tip_share_percent', 0) or 0
        profile.insurance_amount = validated_data.get('insurance_amount', 0) or 0
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
        profile.save(update_fields=['tenant', 'is_available', 'started_at', 'address', 'default_commission_percent', 'default_fixed_wage', 'default_hourly_wage', 'insurance_amount', 'payment_type', 'tip_share_percent', 'has_entrusted_item', 'entrusted_items', 'entrusted_item_description', 'entrusted_item_quantity', 'entrusted_item_price', 'updated_at'])

        return profile

    def update(self, instance, validated_data):
        user_model = get_user_model()
        next_phone = validated_data.get('phone', instance.user.phone)
        next_username = str(validated_data.get('username', instance.user.username) or '').strip()
        is_available = validated_data.get('is_available', instance.is_available)
        if not next_username:
            next_username = instance.user.username or _generate_worker_username(user_model, phone=next_phone)
        if user_model.objects.exclude(id=instance.user_id).filter(phone=next_phone).exists():
            raise serializers.ValidationError({'phone': 'این شماره موبایل قبلا ثبت شده است.'})
        if user_model.objects.exclude(id=instance.user_id).filter(username__iexact=next_username).exists():
            raise serializers.ValidationError({'username': 'این نام کاربری قبلا ثبت شده است.'})
        instance.user.full_name = validated_data.get('full_name', instance.user.full_name)
        instance.user.username = next_username
        instance.user.phone = next_phone
        instance.user.role = validated_data.get('role', instance.user.role or 'worker')
        instance.user.is_active = is_available
        password = str(validated_data.get('password') or '').strip()
        update_fields = ['full_name', 'username', 'phone', 'role', 'is_active']
        if password:
            instance.user.set_password(password)
            update_fields.append('password')
        instance.user.save(update_fields=update_fields)
        instance.is_available = is_available
        instance.started_at = validated_data.get('started_at', instance.started_at)
        instance.address = str(validated_data.get('address', instance.address) or '').strip()
        instance.has_entrusted_item = bool(validated_data.get('has_entrusted_item', instance.has_entrusted_item))
        instance.entrusted_items = validated_data.get('entrusted_items', instance.entrusted_items)
        instance.entrusted_item_description = (validated_data.get('entrusted_item_description', instance.entrusted_item_description) or '').strip()
        instance.entrusted_item_quantity = validated_data.get('entrusted_item_quantity', instance.entrusted_item_quantity) or 0
        instance.entrusted_item_price = validated_data.get('entrusted_item_price', instance.entrusted_item_price) or 0
        payment_type = validated_data.get('payment_type', 'percent')
        payment_value = validated_data.get('payment_value', 0) or 0
        instance.tip_share_percent = validated_data.get('tip_share_percent', 0) or 0
        instance.insurance_amount = validated_data.get('insurance_amount', instance.insurance_amount) or 0
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
        instance.save(update_fields=['is_available', 'started_at', 'address', 'default_commission_percent', 'default_fixed_wage', 'default_hourly_wage', 'insurance_amount', 'payment_type', 'tip_share_percent', 'has_entrusted_item', 'entrusted_items', 'entrusted_item_description', 'entrusted_item_quantity', 'entrusted_item_price', 'updated_at'])

        return instance
