from rest_framework import serializers

from .models import CustomerGroup, SmsTemplate
from .services import is_valid_iran_mobile, normalize_phone, to_english_digits


class SmsTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmsTemplate
        fields = [
            'id',
            'code',
            'title',
            'body',
            'display_order',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CustomerGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerGroup
        fields = [
            'id',
            'name',
            'description',
            'mode',
            'member_keys',
            'rules',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        mode = attrs.get('mode', getattr(self.instance, 'mode', CustomerGroup.Mode.MANUAL))
        member_keys = attrs.get('member_keys', getattr(self.instance, 'member_keys', []))
        rules = attrs.get('rules', getattr(self.instance, 'rules', {}))

        if mode == CustomerGroup.Mode.MANUAL:
            attrs['member_keys'] = list(dict.fromkeys(member_keys or []))
            attrs['rules'] = {}
        else:
            attrs['member_keys'] = []
            attrs['rules'] = {
                'minOrders': max(0, int(float((rules or {}).get('minOrders') or 0))),
                'minSpent': max(0, float((rules or {}).get('minSpent') or 0)),
                'minScore': max(0, float((rules or {}).get('minScore') or 0)),
                'carwash': str((rules or {}).get('carwash') or '').strip(),
            }
        return attrs


class SmsSendRecipientSerializer(serializers.Serializer):
    key = serializers.CharField(required=False, allow_blank=True)
    name = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField()
    carwash_name = serializers.CharField(required=False, allow_blank=True)
    orders_count = serializers.IntegerField(required=False)
    total_spent = serializers.FloatField(required=False)
    score = serializers.FloatField(required=False)
    last_order_at = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    primary_plate = serializers.CharField(required=False, allow_blank=True)

    def validate_phone(self, value):
        phone = normalize_phone(value)
        if not is_valid_iran_mobile(phone):
            raise serializers.ValidationError('شماره گیرنده باید موبایل معتبر و با 09 شروع شود.')
        return phone


class SmsCampaignSendSerializer(serializers.Serializer):
    template_code = serializers.CharField(required=False, allow_blank=True, max_length=60)
    template_text = serializers.CharField(trim_whitespace=False)
    recipients = SmsSendRecipientSerializer(many=True, allow_empty=False)
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)
    target_label = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate_template_text(self, value):
        text = str(value or '').strip()
        if not text:
            raise serializers.ValidationError('متن پیامک نمی‌تواند خالی باشد.')
        return text


class SimpleSmsSendSerializer(serializers.Serializer):
    text = serializers.CharField(trim_whitespace=False)
    recipients = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False,
    )
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)
    target_label = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate_text(self, value):
        text = str(value or '').strip()
        if not text:
            raise serializers.ValidationError('متن پیامک نمی‌تواند خالی باشد.')
        return text

    def validate_recipients(self, value):
        normalized = []
        for recipient in value:
            phone = to_english_digits(recipient)
            phone = ''.join(char for char in phone if char.isdigit())
            if phone.startswith('98') and len(phone) == 12:
                phone = f'0{phone[2:]}'
            if not is_valid_iran_mobile(phone):
                raise serializers.ValidationError('شماره گیرنده باید موبایل معتبر و با 09 شروع شود.')
            normalized.append(phone)
        return list(dict.fromkeys(normalized))
