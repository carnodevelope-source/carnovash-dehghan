from django.utils import timezone

from apps.notifications.models import NotificationLog
from apps.notifications.services import (
    debit_sms_wallets,
    is_valid_iran_mobile,
    make_json_safe,
    normalize_phone,
    send_provider_sms,
    sms_billable_text,
    sms_cost_for_text,
    sms_price_per_segment,
    sms_segments_for_text,
    sms_wallet_balance,
)


def role_sms_label(role):
    return {
        'manager': 'مدیر',
        'admin': 'ادمین',
        'operator': 'اپراتور',
        'accountant': 'حسابدار',
        'worker': 'نیرو',
        'hq_support': 'پشتیبان مرکزی',
    }.get(role, 'کاربر')


def create_sms_log(*, tenant, recipient, template_code, payload, result, created_by=None):
    NotificationLog.objects.create(
        tenant=tenant,
        channel=NotificationLog.Channel.SMS,
        recipient=recipient or '',
        template_code=template_code,
        payload=make_json_safe(payload or {}),
        status=NotificationLog.Status.SENT if result.get('ok') else NotificationLog.Status.FAILED,
        sent_at=timezone.now() if result.get('ok') else None,
        provider_message_id=str(result.get('provider_id') or ''),
        provider_response=str(result.get('raw_body') or result.get('message') or ''),
        created_by=created_by if getattr(created_by, 'is_authenticated', False) else None,
    )


def send_logged_sms(*, tenant, text, phone, template_code, payload=None, created_by=None, description='ارسال پیامک', reference_type='system_sms', charge_tenant_wallet=True):
    normalized_phone = normalize_phone(phone)
    base_payload = {
        **(payload or {}),
        'text': text,
        'recipient': normalized_phone,
    }
    if not is_valid_iran_mobile(normalized_phone):
        result = {'ok': False, 'message': 'شماره موبایل معتبر نیست و باید با 09 شروع شود.'}
        create_sms_log(
            tenant=tenant,
            recipient=normalized_phone or phone,
            template_code=template_code,
            payload=base_payload,
            result=result,
            created_by=created_by,
        )
        return result

    sms_price = sms_price_per_segment()
    segments = sms_segments_for_text(text)
    estimated_cost = sms_cost_for_text(text)
    character_count = len(sms_billable_text(text))
    if charge_tenant_wallet and tenant and sms_wallet_balance(tenant) < estimated_cost:
        result = {'ok': False, 'message': 'موجودی کیف پول پیامک کافی نیست.'}
        create_sms_log(
            tenant=tenant,
            recipient=normalized_phone,
            template_code=template_code,
            payload={
                **base_payload,
                'character_count': character_count,
                'estimated_cost': float(estimated_cost),
                'segments': segments,
                'price_per_segment': float(sms_price),
            },
            result=result,
            created_by=created_by,
        )
        return result

    provider_result = send_provider_sms(tenant, text, [normalized_phone])
    log_payload = {
        **base_payload,
        'character_count': character_count,
        'estimated_cost': float(estimated_cost),
        'segments': segments,
        'price_per_segment': float(sms_price),
        'provider_request': make_json_safe(provider_result.get('payload', {})),
    }
    create_sms_log(
        tenant=tenant,
        recipient=normalized_phone,
        template_code=template_code,
        payload=log_payload,
        result=provider_result,
        created_by=created_by,
    )
    if provider_result.get('ok') and tenant and charge_tenant_wallet:
        debit_sms_wallets(
            tenant,
            estimated_cost,
            description=description,
            reference_type=reference_type,
            created_by=created_by,
        )
    return provider_result


def send_user_credentials_sms(*, tenant, tenant_name, phone, username, password, role, created_by=None, template_code='user_credentials'):
    text = (
        f'{role_sms_label(role)} جدید برای {tenant_name} ثبت شد.\n'
        f'نام کاربری: {username}\n'
        f'رمز عبور: {password}\n'
        f'ورود از پنل کارنوواش'
    )
    return send_logged_sms(
        tenant=tenant,
        text=text,
        phone=phone,
        template_code=template_code,
        payload={'username': username, 'role': role, 'tenant_name': tenant_name},
        created_by=created_by,
        description='ارسال پیامک اطلاعات ورود کاربر',
        reference_type=template_code,
        charge_tenant_wallet=False,
    )


def send_registration_credentials_sms(*, tenant, carwash_name, phone, username, password, created_by=None):
    text = (
        f'ثبت کارواش {carwash_name} انجام شد.\n'
        f'نام کاربری: {username}\n'
        f'رمز عبور: {password}\n'
        f'با تشکر از انتخاب خوب شما  -  کارنوواش'
    )
    return send_logged_sms(
        tenant=tenant,
        text=text,
        phone=phone,
        template_code='tenant_registration_credentials',
        payload={'username': username, 'carwash_name': carwash_name},
        created_by=created_by,
        description='ارسال پیامک اطلاعات ورود مدیر کارواش',
        reference_type='tenant_registration_credentials',
        charge_tenant_wallet=False,
    )
