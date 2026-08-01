from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers

from .feature_access import feature_access_map_for_tenant
from .models import CarWash, CarWashFeaturePurchase, PendingTenantRegistration, SupportTicket, SupportTicketAttachment, SupportTicketMessage


def feature_access_map(feature_keys):
    feature_key_set = set(feature_keys or [])
    return {
        key: key in feature_key_set
        for key in CarWashFeaturePurchase.FeatureKey.values
    }


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username_or_phone = attrs.get('username', '').strip()
        password = attrs.get('password')

        resolved_username = username_or_phone
        user_model = get_user_model()

        user_by_phone = user_model.objects.filter(phone=username_or_phone).first()
        if user_by_phone:
            resolved_username = user_by_phone.username

        user = user_model.objects.filter(username=resolved_username).select_related('tenant').first()
        if not user or not user.check_password(password):
            raise serializers.ValidationError('نام کاربری یا رمز عبور اشتباه است.')
        if not user.is_active:
            pending_request = getattr(getattr(user, 'tenant', None), 'pending_registration', None)
            if pending_request and pending_request.status == PendingTenantRegistration.Status.PENDING:
                raise serializers.ValidationError('ثبت‌نام شما هنوز توسط پشتیبانی تایید نشده است. بعد از تایید، پیامک فعال‌سازی برای شما ارسال می‌شود.')
            raise serializers.ValidationError('حساب کاربری غیرفعال است.')

        attrs['user'] = user
        return attrs


class UserListSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    menu_access = serializers.SerializerMethodField()
    purchased_menu_access = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = [
            'id',
            'username',
            'full_name',
            'first_name',
            'last_name',
            'phone',
            'tenant',
            'tenant_name',
            'menu_access',
            'purchased_menu_access',
            'role',
            'platform_role',
            'is_active',
        ]

    def get_menu_access(self, obj):
        return feature_access_map_for_tenant(getattr(obj, 'tenant', None))

    def get_purchased_menu_access(self, obj):
        if not getattr(obj, 'tenant_id', None):
            return []
        return obj.tenant.active_feature_keys()


class HqSupportUserListSerializer(UserListSerializer):
    support_star_rating = serializers.DecimalField(max_digits=4, decimal_places=2, read_only=True)
    support_rating_count = serializers.IntegerField(read_only=True)
    support_customer_satisfaction_avg = serializers.DecimalField(max_digits=4, decimal_places=2, read_only=True)
    support_response_quality_avg = serializers.DecimalField(max_digits=4, decimal_places=2, read_only=True)
    support_first_response_minutes_avg = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    support_total_responses = serializers.IntegerField(read_only=True)
    support_resolved_tickets_count = serializers.IntegerField(read_only=True)

    class Meta(UserListSerializer.Meta):
        fields = UserListSerializer.Meta.fields + [
            'support_star_rating',
            'support_rating_count',
            'support_customer_satisfaction_avg',
            'support_response_quality_avg',
            'support_first_response_minutes_avg',
            'support_total_responses',
            'support_resolved_tickets_count',
        ]


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)

    class Meta:
        model = get_user_model()
        fields = [
            'username',
            'full_name',
            'first_name',
            'last_name',
            'phone',
            'role',
            'password',
            'is_active',
        ]

    def validate_role(self, value):
        request = self.context.get('request')
        if not request or not request.user:
            return value

        if getattr(request.user, 'role', '') == 'manager' and value in ['admin', 'owner']:
            raise serializers.ValidationError('مدیر نمی‌تواند کاربر ادمین یا مالک ایجاد کند.')
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        request = self.context.get('request')
        tenant = getattr(getattr(request, 'user', None), 'tenant', None)
        user_model = get_user_model()
        first_name = str(validated_data.get('first_name', '') or '').strip()
        last_name = str(validated_data.get('last_name', '') or '').strip()
        full_name = str(validated_data.get('full_name', '') or '').strip()
        if not full_name:
            validated_data['full_name'] = f'{first_name} {last_name}'.strip()
        validated_data['tenant'] = tenant
        user = user_model(**validated_data)
        user.set_password(password)
        user.save()
        user._raw_password = password
        return user


class TenantRegisterSerializer(serializers.Serializer):
    carwash_name = serializers.CharField(max_length=150)
    carwash_address = serializers.CharField(max_length=300, required=False, allow_blank=True)
    carwash_slug = serializers.SlugField(max_length=160, required=False, allow_blank=True)
    manager_full_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    manager_first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    manager_last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    manager_username = serializers.CharField(max_length=150)
    manager_phone = serializers.CharField(max_length=20)
    manager_password = serializers.CharField(write_only=True, min_length=6)

    def validate(self, attrs):
        first_name = str(attrs.get('manager_first_name', '') or '').strip()
        last_name = str(attrs.get('manager_last_name', '') or '').strip()
        full_name = str(attrs.get('manager_full_name', '') or '').strip()

        if not full_name:
            full_name = f'{first_name} {last_name}'.strip()
        if not full_name:
            raise serializers.ValidationError({'manager_first_name': ['نام مدیر را وارد کنید.']})

        if not first_name and full_name:
            parts = full_name.split()
            attrs['manager_first_name'] = parts[0]
            attrs['manager_last_name'] = ' '.join(parts[1:]) if len(parts) > 1 else ''
        else:
            attrs['manager_first_name'] = first_name
            attrs['manager_last_name'] = last_name

        attrs['manager_full_name'] = full_name
        attrs['carwash_address'] = str(attrs.get('carwash_address', '') or '').strip()
        attrs['carwash_slug'] = str(attrs.get('carwash_slug', '') or '').strip()
        return attrs


class CarWashManagerSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = [
            'id',
            'username',
            'full_name',
            'first_name',
            'last_name',
            'phone',
            'is_active',
        ]


class CarWashListSerializer(serializers.ModelSerializer):
    manager = serializers.SerializerMethodField()
    tickets_open_count = serializers.SerializerMethodField()
    purchased_menu_access = serializers.SerializerMethodField()
    menu_access = serializers.SerializerMethodField()

    class Meta:
        model = CarWash
        fields = [
            'id',
            'name',
            'slug',
            'address',
            'is_active',
            'exclude_from_hq_reports',
            'created_at',
            'updated_at',
            'manager',
            'tickets_open_count',
            'purchased_menu_access',
            'menu_access',
        ]

    def get_manager(self, obj):
        manager = get_user_model().objects.filter(tenant=obj, role='manager').order_by('id').first()
        if not manager:
            return None
        return CarWashManagerSerializer(manager).data

    def get_tickets_open_count(self, obj):
        return obj.support_tickets.exclude(status=SupportTicket.Status.CLOSED).count()

    def get_purchased_menu_access(self, obj):
        return obj.active_feature_keys()

    def get_menu_access(self, obj):
        return feature_access_map_for_tenant(obj)


class CarWashCreateSerializer(serializers.Serializer):
    carwash_name = serializers.CharField(max_length=150)
    carwash_address = serializers.CharField(max_length=300, required=False, allow_blank=True)
    manager_first_name = serializers.CharField(max_length=150)
    manager_last_name = serializers.CharField(max_length=150)
    manager_username = serializers.CharField(max_length=150)
    manager_phone = serializers.CharField(max_length=20)
    manager_password = serializers.CharField(min_length=6, write_only=True)
    purchased_menu_access = serializers.ListField(
        child=serializers.ChoiceField(choices=CarWashFeaturePurchase.FeatureKey.choices),
        required=False,
        allow_empty=True,
    )


class CarWashUpdateSerializer(serializers.Serializer):
    carwash_name = serializers.CharField(max_length=150, required=False)
    carwash_address = serializers.CharField(max_length=300, required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)
    exclude_from_hq_reports = serializers.BooleanField(required=False)
    manager_first_name = serializers.CharField(max_length=150, required=False)
    manager_last_name = serializers.CharField(max_length=150, required=False)
    manager_phone = serializers.CharField(max_length=20, required=False)
    manager_password = serializers.CharField(min_length=6, required=False, write_only=True)
    purchased_menu_access = serializers.ListField(
        child=serializers.ChoiceField(choices=CarWashFeaturePurchase.FeatureKey.choices),
        required=False,
        allow_empty=True,
    )


class HqSupportUserCreateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    username = serializers.CharField(max_length=150, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    tenant_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_first_name(self, value):
        value = str(value or '').strip()
        return value

    def validate_last_name(self, value):
        value = str(value or '').strip()
        return value

    def validate_username(self, value):
        value = str(value or '').strip()
        return value

    def validate_phone(self, value):
        value = str(value or '').strip()
        return value

    def validate_password(self, value):
        value = str(value or '').strip()
        if len(value) < 6:
            raise serializers.ValidationError('رمز عبور پشتیبان باید حداقل ۶ کاراکتر باشد.')
        return value

    def validate_tenant_id(self, value):
        if value in (None, 0, '0', ''):
            return None
        tenant = CarWash.objects.filter(pk=value, is_active=True, exclude_from_hq_reports=False).first()
        if not tenant:
            raise serializers.ValidationError('کارواش انتخاب‌شده معتبر نیست.')
        return tenant.id

    def create(self, validated_data):
        tenant_id = validated_data.get('tenant_id')
        tenant = CarWash.objects.filter(pk=tenant_id).first() if tenant_id else None
        first_name = validated_data.get('first_name') or 'پشتیبان'
        last_name = validated_data.get('last_name') or 'مرکزی'
        full_name = f'{first_name} {last_name}'.strip()[:150]
        user_model = get_user_model()
        username = (validated_data.get('username') or '').strip()
        if not username:
            username = f"support_{first_name}_{last_name}".strip('_').replace(' ', '_')
        base_username = username[:150] or 'support_user'
        counter = 1
        while user_model.objects.filter(username__iexact=username).exists():
            counter += 1
            suffix = f'_{counter}'
            username = f"{base_username[: max(1, 150 - len(suffix))]}{suffix}"
        phone = (validated_data.get('phone') or '').strip()
        if not phone:
            phone = f'0999{user_model.objects.count() + 1:07d}'
        base_phone = phone[:20] or '09990000000'
        phone_counter = 1
        while user_model.objects.filter(phone=phone).exists():
            phone_counter += 1
            suffix = str(phone_counter)
            trimmed = base_phone[: max(1, 20 - len(suffix))]
            phone = f'{trimmed}{suffix}'
        password = str(validated_data.get('password') or '').strip()
        user = user_model.objects.create(
            username=username,
            first_name=first_name,
            last_name=last_name,
            full_name=full_name,
            phone=phone,
            tenant=tenant,
            role='admin',
            platform_role='hq_support',
            is_active=True,
            is_staff=True,
            is_superuser=False,
        )
        user.set_password(password)
        user.save(update_fields=['password'])
        user._raw_password = password
        return user


class HqSupportUserUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    username = serializers.CharField(max_length=150, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    tenant_id = serializers.IntegerField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False)

    def validate_username(self, value):
        return str(value or '').strip()

    def validate_phone(self, value):
        return str(value or '').strip()

    def validate_password(self, value):
        value = str(value or '').strip()
        if value and len(value) < 6:
            raise serializers.ValidationError('رمز عبور پشتیبان باید حداقل ۶ کاراکتر باشد.')
        return value

    def validate_tenant_id(self, value):
        if value in (None, 0, '0', ''):
            return None
        tenant = CarWash.objects.filter(pk=value, is_active=True, exclude_from_hq_reports=False).first()
        if not tenant:
            raise serializers.ValidationError('کارواش انتخاب‌شده معتبر نیست.')
        return tenant.id


class SupportTicketMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    sender_role = serializers.SerializerMethodField()
    sender_platform_role = serializers.CharField(source='sender.platform_role', read_only=True)

    class Meta:
        model = SupportTicketMessage
        fields = [
            'id',
            'sender',
            'sender_name',
            'sender_role',
            'sender_platform_role',
            'body',
            'is_internal',
            'created_at',
        ]

    def get_sender_name(self, obj):
        if not obj.sender:
            return '-'
        return obj.sender.full_name or obj.sender.username

    def get_sender_role(self, obj):
        if not obj.sender:
            return ''
        if obj.sender.platform_role:
            return obj.sender.get_platform_role_display()
        return obj.sender.get_role_display()


class SupportTicketAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicketAttachment
        fields = ['id', 'original_name', 'file_url', 'created_at']

    def get_file_url(self, obj):
        if not obj.file:
            return ''
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url


class SupportTicketListSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    responded_by_name = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()
    messages_count = serializers.SerializerMethodField()
    last_message_preview = serializers.SerializerMethodField()
    is_registration_request = serializers.BooleanField(read_only=True)
    registration_status = serializers.SerializerMethodField()
    registration_manager_username = serializers.SerializerMethodField()
    registration_manager_phone = serializers.SerializerMethodField()
    is_wallet_card_payment = serializers.SerializerMethodField()
    is_wallet_bank_withdrawal = serializers.SerializerMethodField()
    can_wallet_transfer = serializers.SerializerMethodField()
    can_wallet_withdraw = serializers.SerializerMethodField()
    suggested_wallet_amount = serializers.SerializerMethodField()
    wallet_id = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicket
        fields = [
            'id',
            'tenant',
            'tenant_name',
            'created_by',
            'created_by_name',
            'subject',
            'message',
            'category',
            'priority',
            'status',
            'response_text',
            'assigned_to',
            'assigned_to_name',
            'responded_by_name',
            'first_response_at',
            'responded_at',
            'response_quality_score',
            'customer_satisfaction',
            'customer_feedback',
            'last_message_at',
            'messages_count',
            'last_message_preview',
            'is_registration_request',
            'registration_status',
            'registration_manager_username',
            'registration_manager_phone',
            'is_wallet_card_payment',
            'is_wallet_bank_withdrawal',
            'can_wallet_transfer',
            'can_wallet_withdraw',
            'suggested_wallet_amount',
            'wallet_id',
            'created_at',
            'updated_at',
        ]

    def get_created_by_name(self, obj):
        if not obj.created_by:
            return '-'
        return obj.created_by.full_name or obj.created_by.username

    def get_responded_by_name(self, obj):
        if not obj.responded_by:
            return '-'
        return obj.responded_by.full_name or obj.responded_by.username

    def get_assigned_to_name(self, obj):
        if not obj.assigned_to:
            return '-'
        return obj.assigned_to.full_name or obj.assigned_to.username

    def get_messages_count(self, obj):
        return getattr(obj, 'messages_count', None) or obj.messages.count()

    def get_last_message_preview(self, obj):
        last_message = getattr(obj, 'last_message_obj', None) or obj.messages.order_by('-created_at', '-id').first()
        if not last_message:
            return (obj.message or '')[:120]
        return (last_message.body or '')[:120]

    def _registration_request(self, obj):
        return getattr(obj, 'registration_request', None)

    def get_registration_status(self, obj):
        request = self._registration_request(obj)
        if not request:
            return ''
        return request.status

    def get_registration_manager_username(self, obj):
        request = self._registration_request(obj)
        if not request or not request.manager_id:
            return ''
        return request.manager.username

    def get_registration_manager_phone(self, obj):
        request = self._registration_request(obj)
        if not request or not request.manager_id:
            return ''
        return request.manager.phone

    def get_is_wallet_card_payment(self, obj):
        from .support_tickets import is_wallet_card_payment_ticket
        return is_wallet_card_payment_ticket(obj)

    def get_is_wallet_bank_withdrawal(self, obj):
        from .support_tickets import is_wallet_bank_withdrawal_ticket
        return is_wallet_bank_withdrawal_ticket(obj)

    def get_can_wallet_transfer(self, obj):
        return bool(self.get_is_wallet_card_payment(obj) and obj.status != SupportTicket.Status.CLOSED)

    def get_can_wallet_withdraw(self, obj):
        return bool(self.get_is_wallet_bank_withdrawal(obj) and obj.status != SupportTicket.Status.CLOSED)

    def get_suggested_wallet_amount(self, obj):
        from .support_tickets import parse_wallet_amount_from_ticket
        amount = parse_wallet_amount_from_ticket(obj)
        return float(amount) if amount > 0 else 0

    def get_wallet_id(self, obj):
        from .support_tickets import parse_wallet_id_from_ticket
        return parse_wallet_id_from_ticket(obj)

class SupportTicketDetailSerializer(SupportTicketListSerializer):
    messages = SupportTicketMessageSerializer(many=True, read_only=True)
    attachments = SupportTicketAttachmentSerializer(many=True, read_only=True)

    class Meta(SupportTicketListSerializer.Meta):
        fields = SupportTicketListSerializer.Meta.fields + ['messages', 'attachments']


class SupportTicketCreateSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=180)
    message = serializers.CharField()
    category = serializers.ChoiceField(choices=SupportTicket.Category.choices, required=False)
    priority = serializers.ChoiceField(choices=SupportTicket.Priority.choices, required=False)


class SupportTicketReplySerializer(serializers.Serializer):
    body = serializers.CharField()
    status = serializers.ChoiceField(choices=SupportTicket.Status.choices, required=False)
    assign_to_user_id = serializers.IntegerField(required=False)
    is_internal = serializers.BooleanField(required=False, default=False)


class SupportTicketFeedbackSerializer(serializers.Serializer):
    customer_satisfaction = serializers.IntegerField(min_value=1, max_value=5)
    customer_feedback = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class HqTicketWalletTransferSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=1)
    wallet_id = serializers.IntegerField(required=False)
