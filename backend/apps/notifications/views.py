import json
import math
import uuid
from collections import Counter
from decimal import Decimal
from urllib import error as urllib_error
from urllib import request as urllib_request

from django.conf import settings
from django.db import transaction
from django.db.models import Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments.models import CashflowTransaction, Wallet
from .models import CustomerGroup, NotificationLog, SmsTemplate
from .serializers import (
    CustomerGroupSerializer,
    SimpleSmsSendSerializer,
    SmsCampaignSendSerializer,
    SmsTemplateSerializer,
)
from .services import (
    build_customer_summaries,
    ensure_default_sms_templates,
    extract_log_metadata,
    group_sms_batches,
)


class SmsWalletMixin:
    def _get_sms_wallets_for_update(self, tenant):
        wallets = list(
            Wallet.objects.select_for_update()
            .filter(
                tenant=tenant,
                wallet_type=Wallet.WalletType.SMS,
                is_active=True,
            )
            .order_by('id')
        )
        if wallets:
            return wallets

        wallet = Wallet.objects.create(
            tenant=tenant,
            name='کیف پول پیامک',
            wallet_type=Wallet.WalletType.SMS,
            balance=0,
            is_active=True,
        )
        return [wallet]

    def _sms_wallet_balance(self, tenant):
        return (
            Wallet.objects.filter(
                tenant=tenant,
                wallet_type=Wallet.WalletType.SMS,
                is_active=True,
            ).aggregate(
                total=Coalesce(Sum('balance'), Value(Decimal('0')))
            )['total']
            or Decimal('0')
        )

    def _debit_sms_wallets(self, tenant, amount, *, description, reference_type, created_by=None):
        remaining = Decimal(str(amount or 0))
        wallets = self._get_sms_wallets_for_update(tenant)
        for wallet in wallets:
            if remaining <= 0:
                break
            current_balance = Decimal(str(wallet.balance or 0))
            if current_balance <= 0:
                continue
            debit = min(current_balance, remaining)
            wallet.balance = current_balance - debit
            wallet.save(update_fields=['balance', 'updated_at'])
            CashflowTransaction.objects.create(
                tenant=tenant,
                wallet=wallet,
                direction=CashflowTransaction.Direction.OUT,
                amount=debit,
                description=description,
                reference_type=reference_type,
                created_by=created_by if getattr(created_by, 'is_authenticated', False) else None,
            )
            remaining -= debit

        if remaining > 0:
            raise ValidationError({'detail': 'موجودی کیف پول پیامک کافی نیست.'})


class SmsProviderMixin:
    provider_url = '/ws/v1/sms/simple'

    def _provider_config(self):
        api_key = str(getattr(settings, 'IRANPAYAMAK_API_KEY', '') or '').strip()
        line_number = str(getattr(settings, 'IRANPAYAMAK_LINE_NUMBER', '') or '').strip()
        base_url = str(getattr(settings, 'IRANPAYAMAK_BASE_URL', 'https://api.iranpayamak.com') or '').rstrip('/')
        if not api_key or not line_number:
            raise ValidationError({'detail': 'تنظیمات سرویس پیامک کامل نیست.'})
        return {
            'api_key': api_key,
            'line_number': line_number,
            'base_url': base_url,
        }

    def _provider_message_text(self, provider_data, fallback='ارسال پیامک توسط سرویس تایید نشد.'):
        if isinstance(provider_data, dict):
            message = provider_data.get('message') or provider_data.get('messages')
            if isinstance(message, list):
                return ' | '.join(str(item) for item in message if item)
            if isinstance(message, dict):
                return json.dumps(message, ensure_ascii=False)
            if message:
                try:
                    return bytes(str(message), 'utf-8').decode('unicode_escape')
                except Exception:
                    return str(message)
        if provider_data:
            return str(provider_data)
        return fallback

    def _send_provider_request(self, *, text, recipients):
        config = self._provider_config()
        payload = {
            'text': text,
            'line_number': config['line_number'],
            'recipients': recipients,
            'number_format': 'english',
            'schedule': None,
        }
        req = urllib_request.Request(
            url=f"{config['base_url']}{self.provider_url}",
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'Api-Key': config['api_key'],
            },
            method='POST',
        )

        try:
            with urllib_request.urlopen(req, timeout=15) as response:
                raw_body = response.read().decode('utf-8')
                response_status = response.status
        except urllib_error.HTTPError as exc:
            raw_body = exc.read().decode('utf-8', errors='replace')
            try:
                provider_data = json.loads(raw_body or '{}')
            except json.JSONDecodeError:
                provider_data = {'message': raw_body}
            return {
                'ok': False,
                'provider_status': exc.code,
                'raw_body': raw_body,
                'provider_data': provider_data,
                'message': self._provider_message_text(provider_data, fallback='سرویس پیامک درخواست را نپذیرفت.'),
                'payload': payload,
            }
        except urllib_error.URLError as exc:
            provider_response = str(getattr(exc, 'reason', exc))
            return {
                'ok': False,
                'provider_status': 0,
                'raw_body': provider_response,
                'provider_data': {'message': provider_response},
                'message': 'ارتباط با سرویس پیامک برقرار نشد.',
                'payload': payload,
            }

        try:
            provider_data = json.loads(raw_body or '{}')
        except json.JSONDecodeError:
            provider_data = {'status': 'error', 'message': raw_body}

        if response_status not in {200, 201} or provider_data.get('status') != 'success':
            return {
                'ok': False,
                'provider_status': response_status,
                'raw_body': raw_body,
                'provider_data': provider_data,
                'message': self._provider_message_text(provider_data),
                'payload': payload,
            }

        data = provider_data.get('data')
        provider_id = ''
        provider_delivery_status = ''
        if isinstance(data, dict):
            provider_id = str(data.get('id') or '')
            provider_delivery_status = str(data.get('status') or '')
        elif data is not None:
            provider_id = str(data)

        return {
            'ok': True,
            'provider_status': response_status,
            'raw_body': raw_body,
            'provider_data': provider_data,
            'message': 'پیامک با موفقیت در صف ارسال قرار گرفت.',
            'provider_id': provider_id,
            'provider_delivery_status': provider_delivery_status,
            'payload': payload,
        }


class CustomerClubDashboardView(APIView, SmsWalletMixin):
    def get(self, request):
        tenant = getattr(request.user, 'tenant', None)
        ensure_default_sms_templates(tenant, request.user)
        customers = build_customer_summaries(tenant)
        templates = SmsTemplate.objects.filter(tenant=tenant, is_active=True).order_by('display_order', 'title', 'id')
        groups = CustomerGroup.objects.filter(tenant=tenant, is_active=True).order_by('-created_at', '-id')
        logs = NotificationLog.objects.filter(tenant=tenant, channel=NotificationLog.Channel.SMS).order_by('-created_at')[:100]
        status_counts = Counter(log.status for log in logs)

        return Response(
            {
                'summary': {
                    'sms_balance': self._sms_wallet_balance(tenant),
                    'sms_price_per_segment': getattr(settings, 'SMS_PRICE_PER_SEGMENT', 500),
                    'status_counts': {
                        'success': status_counts.get(NotificationLog.Status.SENT, 0),
                        'pending': status_counts.get(NotificationLog.Status.PENDING, 0),
                        'failed': status_counts.get(NotificationLog.Status.FAILED, 0),
                    },
                },
                'customers': customers,
                'groups': CustomerGroupSerializer(groups, many=True).data,
                'templates': SmsTemplateSerializer(templates, many=True).data,
                'logs': [extract_log_metadata(log) for log in logs],
            }
        )


class CustomerGroupListCreateView(generics.ListCreateAPIView):
    serializer_class = CustomerGroupSerializer

    def get_queryset(self):
        return CustomerGroup.objects.filter(
            tenant=self.request.user.tenant,
            is_active=True,
        ).order_by('-created_at', '-id')

    def perform_create(self, serializer):
        serializer.save(
            tenant=self.request.user.tenant,
            created_by=self.request.user if getattr(self.request.user, 'is_authenticated', False) else None,
            updated_by=self.request.user if getattr(self.request.user, 'is_authenticated', False) else None,
        )


class CustomerGroupDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CustomerGroupSerializer

    def get_queryset(self):
        return CustomerGroup.objects.filter(tenant=self.request.user.tenant, is_active=True)

    def perform_update(self, serializer):
        serializer.save(
            updated_by=self.request.user if getattr(self.request.user, 'is_authenticated', False) else None,
        )

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.updated_by = self.request.user if getattr(self.request.user, 'is_authenticated', False) else None
        instance.save(update_fields=['is_active', 'updated_by', 'updated_at'])


class SmsTemplateListCreateView(generics.ListCreateAPIView):
    serializer_class = SmsTemplateSerializer

    def get_queryset(self):
        tenant = self.request.user.tenant
        ensure_default_sms_templates(tenant, self.request.user)
        return SmsTemplate.objects.filter(tenant=tenant, is_active=True).order_by('display_order', 'title', 'id')

    def perform_create(self, serializer):
        serializer.save(
            tenant=self.request.user.tenant,
            created_by=self.request.user if getattr(self.request.user, 'is_authenticated', False) else None,
        )


class SmsTemplateDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SmsTemplateSerializer

    def get_queryset(self):
        return SmsTemplate.objects.filter(tenant=self.request.user.tenant, is_active=True)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])


class SmsCampaignSendView(APIView, SmsWalletMixin, SmsProviderMixin):
    def _create_log_entries(self, *, tenant, request_user, recipients, status_value, provider_message_id='', provider_response='', extra_payload=None):
        extra_payload = extra_payload or {}
        sent_at = timezone.now() if status_value == NotificationLog.Status.SENT else None
        logs = []
        for recipient in recipients:
            payload = {
                **extra_payload,
                'recipient_name': recipient.get('name', ''),
                'customer': {
                    'key': recipient.get('key', ''),
                    'name': recipient.get('name', ''),
                    'phone': recipient.get('phone', ''),
                    'carwash_name': recipient.get('carwash_name', ''),
                    'orders_count': recipient.get('orders_count', 0),
                    'total_spent': recipient.get('total_spent', 0),
                    'score': recipient.get('score', 0),
                    'primary_plate': recipient.get('primary_plate', ''),
                },
                'rendered_text': recipient.get('rendered_text', ''),
            }
            logs.append(
                NotificationLog(
                    tenant=tenant,
                    channel=NotificationLog.Channel.SMS,
                    recipient=recipient.get('phone', ''),
                    template_code=extra_payload.get('template_code', ''),
                    payload=payload,
                    status=status_value,
                    sent_at=sent_at,
                    provider_message_id=str(provider_message_id or ''),
                    provider_response=provider_response,
                    created_by=request_user if getattr(request_user, 'is_authenticated', False) else None,
                )
            )
        NotificationLog.objects.bulk_create(logs)

    def _send_validated_campaign(self, request, validated):
        tenant = getattr(request.user, 'tenant', None)
        recipients = validated['recipients']
        template_text = validated['template_text']
        sms_price = Decimal(str(getattr(settings, 'SMS_PRICE_PER_SEGMENT', 500) or 500))
        campaign_id = str(uuid.uuid4())
        grouped_batches, rendered_recipients = group_sms_batches(recipients, template_text, getattr(tenant, 'name', ''))

        estimated_total = Decimal('0')
        for recipient in rendered_recipients:
            segments = max(1, math.ceil(len(str(recipient.get('rendered_text') or '').strip()) / 70))
            estimated_total += sms_price * Decimal(segments)

        wallet_balance = self._sms_wallet_balance(tenant)
        if wallet_balance < estimated_total:
            return Response(
                {
                    'detail': 'موجودی کیف پول پیامک کافی نیست.',
                    'required_amount': estimated_total,
                    'wallet_balance': wallet_balance,
                },
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        results = []
        success_count = 0
        failed_count = 0
        debited_amount = Decimal('0')

        for rendered_text, batch_recipients in grouped_batches.items():
            phone_numbers = [recipient['phone'] for recipient in batch_recipients]
            provider_result = self._send_provider_request(text=rendered_text, recipients=phone_numbers)
            segments = max(1, math.ceil(len(str(rendered_text or '').strip()) / 70))
            batch_cost = sms_price * Decimal(segments) * Decimal(len(batch_recipients))
            extra_payload = {
                'campaign_id': campaign_id,
                'target_label': validated.get('target_label', ''),
                'note': validated.get('note', ''),
                'template_code': validated.get('template_code', ''),
                'template_text': template_text,
                'segments': segments,
                'price_per_segment': str(sms_price),
                'total_cost': str(batch_cost),
                'provider_request': provider_result['payload'],
            }

            if provider_result['ok']:
                with transaction.atomic():
                    self._debit_sms_wallets(
                        tenant,
                        batch_cost,
                        description=f'ارسال پیامک: {validated.get("target_label", "").strip() or "باشگاه مشتریان"}',
                        reference_type='sms_campaign_send',
                        created_by=request.user,
                    )
                debited_amount += batch_cost
                self._create_log_entries(
                    tenant=tenant,
                    request_user=request.user,
                    recipients=batch_recipients,
                    status_value=NotificationLog.Status.SENT,
                    provider_message_id=provider_result.get('provider_id', ''),
                    provider_response=provider_result['raw_body'],
                    extra_payload=extra_payload,
                )
                for recipient in batch_recipients:
                    success_count += 1
                    results.append(
                        {
                            'phone': recipient['phone'],
                            'recipient_name': recipient.get('name', ''),
                            'status': 'success',
                            'message': provider_result['message'],
                            'provider_message_id': provider_result.get('provider_id', ''),
                            'rendered_text': recipient.get('rendered_text', ''),
                            'cost': sms_price * Decimal(segments),
                        }
                    )
            else:
                self._create_log_entries(
                    tenant=tenant,
                    request_user=request.user,
                    recipients=batch_recipients,
                    status_value=NotificationLog.Status.FAILED,
                    provider_response=provider_result['raw_body'],
                    extra_payload=extra_payload,
                )
                for recipient in batch_recipients:
                    failed_count += 1
                    results.append(
                        {
                            'phone': recipient['phone'],
                            'recipient_name': recipient.get('name', ''),
                            'status': 'failed',
                            'message': provider_result['message'],
                            'provider_message_id': '',
                            'rendered_text': recipient.get('rendered_text', ''),
                            'cost': sms_price * Decimal(segments),
                        }
                    )

        http_status = status.HTTP_201_CREATED if success_count > 0 else status.HTTP_502_BAD_GATEWAY
        detail = 'پیامک با موفقیت در صف ارسال قرار گرفت.'
        if success_count and failed_count:
            detail = 'بخشی از پیامک‌ها ارسال شد و بخشی ناموفق بود.'
        elif failed_count and not success_count:
            detail = 'هیچ پیامکی ارسال نشد.'

        return Response(
            {
                'detail': detail,
                'campaign_id': campaign_id,
                'success_count': success_count,
                'failed_count': failed_count,
                'debited_amount': debited_amount,
                'results': results,
            },
            status=http_status,
        )

    def post(self, request):
        serializer = SmsCampaignSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._send_validated_campaign(request, serializer.validated_data)


class SimpleSmsSendView(SmsCampaignSendView):
    def post(self, request):
        serializer = SimpleSmsSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recipients = serializer.validated_data['recipients']
        payload = {
            'template_text': serializer.validated_data['text'],
            'target_label': serializer.validated_data.get('target_label', ''),
            'note': serializer.validated_data.get('note', ''),
            'recipients': [
                {
                    'phone': phone,
                    'name': '',
                    'carwash_name': getattr(getattr(request.user, 'tenant', None), 'name', ''),
                }
                for phone in recipients
            ],
        }
        campaign_serializer = SmsCampaignSendSerializer(data=payload)
        campaign_serializer.is_valid(raise_exception=True)
        return self._send_validated_campaign(request, campaign_serializer.validated_data)
