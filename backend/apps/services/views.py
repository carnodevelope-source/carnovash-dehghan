from decimal import Decimal

from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response

from .models import (
    DEFAULT_SMS_VEHICLE_ASSIGNED_INVOICE_TEMPLATE,
    DEFAULT_SMS_VEHICLE_ASSIGNED_TEMPLATE,
    DEFAULT_SMS_VEHICLE_RELEASED_TEMPLATE,
    GeneralSettings,
    Service,
    ServiceChangeLog,
    normalize_vehicle_assigned_sms_template,
    normalize_vehicle_released_sms_template,
)
from .serializers import GeneralSettingsSerializer, ServiceChangeLogSerializer, ServiceSerializer


def _service_snapshot(service):
    return {
        'name': service.name,
        'base_price': service.base_price,
        'estimated_duration_minutes': service.estimated_duration_minutes,
        'is_active': service.is_active,
    }


def _build_change_summary(previous, current):
    def _normalize(value):
        if isinstance(value, Decimal):
            return float(value)
        return value

    summary = {}
    labels = {
        'name': 'نام',
        'base_price': 'قیمت',
        'estimated_duration_minutes': 'مدت',
        'is_active': 'وضعیت',
    }
    for key, label in labels.items():
        old_value = previous.get(key)
        new_value = current.get(key)
        if old_value != new_value:
            summary[key] = {
                'label': label,
                'from': _normalize(old_value),
                'to': _normalize(new_value),
            }
    return summary


def _log_service_change(service, action_type, user=None, previous_snapshot=None):
    current_snapshot = _service_snapshot(service)
    ServiceChangeLog.objects.create(
        tenant=service.tenant,
        service=service,
        action_type=action_type,
        changed_by=user,
        name_snapshot=service.name,
        base_price_snapshot=service.base_price,
        estimated_duration_snapshot=service.estimated_duration_minutes,
        is_active_snapshot=service.is_active,
        change_summary=_build_change_summary(previous_snapshot or {}, current_snapshot),
    )


class ServiceListCreateView(generics.ListCreateAPIView):
    serializer_class = ServiceSerializer

    def get_queryset(self):
        tenant = getattr(self.request.user, 'tenant', None)
        queryset = Service.objects.select_related('category').filter(
            tenant=tenant,
            is_active=True,
            is_deleted=False,
        )
        plate_type = str(self.request.query_params.get('plate_type', '') or '').strip().lower()
        if plate_type == 'motorcycle':
            queryset = queryset.filter(motorcycle_enabled=True)
        return queryset.order_by('display_order', 'name')

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        instance = serializer.save(created_by=user, tenant=getattr(user, 'tenant', None))
        _log_service_change(instance, ServiceChangeLog.ActionType.CREATED, user=user)


class ServiceRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ServiceSerializer

    def get_queryset(self):
        tenant = getattr(self.request.user, 'tenant', None)
        return Service.objects.select_related('category').filter(
            tenant=tenant,
            is_deleted=False,
        ).order_by('display_order', 'name')

    def perform_update(self, serializer):
        instance = self.get_object()
        previous_snapshot = _service_snapshot(instance)
        updated_instance = serializer.save()
        _log_service_change(
            updated_instance,
            ServiceChangeLog.ActionType.UPDATED,
            user=self.request.user if self.request.user.is_authenticated else None,
            previous_snapshot=previous_snapshot,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        previous_snapshot = _service_snapshot(instance)
        if not instance.is_deleted:
            instance.is_active = False
            instance.is_deleted = True
            instance.deleted_at = timezone.now()
            instance.deleted_by = request.user if request.user.is_authenticated else None
            instance.save(update_fields=['is_active', 'is_deleted', 'deleted_at', 'deleted_by', 'updated_at'])
            _log_service_change(
                instance,
                ServiceChangeLog.ActionType.DEACTIVATED,
                user=request.user if request.user.is_authenticated else None,
                previous_snapshot=previous_snapshot,
            )
        return Response({'soft_deleted': True, 'is_active': False}, status=status.HTTP_200_OK)


class ServiceHistoryView(generics.RetrieveAPIView):
    serializer_class = ServiceSerializer

    def get_queryset(self):
        tenant = getattr(self.request.user, 'tenant', None)
        return Service.objects.select_related('category').filter(
            tenant=tenant,
            is_deleted=False,
        ).order_by('display_order', 'name')

    def retrieve(self, request, *args, **kwargs):
        service = self.get_object()
        history = service.change_logs.select_related('changed_by').all()[:5]
        return Response(
            {
                'service': ServiceSerializer(service).data,
                'history': ServiceChangeLogSerializer(history, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


class GeneralSettingsRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = GeneralSettingsSerializer
    queryset = GeneralSettings.objects.all()

    def get_object(self):
        defaults = {
                'discount_percent_per_half_star': 0,
                'discount_calculation_mode': GeneralSettings.DiscountCalculationMode.STEP,
                'fixed_visit_discounts': {'2': 0, '5': 0, '10': 0},
                'tax_enabled': False,
                'tax_percent': 0,
                'preferred_bank_name': '',
                'bank_account_holder': '',
                'bank_card_number': '',
                'bank_account_iban': '',
                'pos_device_name': '',
                'pos_terminal_id': '',
                'payment_methods_note': '',
                'receipt_printer_enabled': False,
                'receipt_printer_name': '',
                'receipt_printer_paper_width': '80mm',
                'receipt_print_copies': 1,
                'receipt_auto_print': False,
                'receipt_show_logo': False,
                'receipt_show_qr': False,
                'receipt_header_note': '',
                'receipt_footer_note': '',
                'sms_provider_base_url': 'https://api.iranpayamak.com',
                'sms_provider_api_key': '',
                'sms_provider_line_number': '',
                'sms_vehicle_auto_send_enabled': True,
                'sms_vehicle_assigned_enabled': True,
                'sms_vehicle_assigned_invoice_enabled': True,
                'sms_vehicle_released_enabled': True,
                'sms_vehicle_assigned_template': DEFAULT_SMS_VEHICLE_ASSIGNED_TEMPLATE,
                'sms_vehicle_assigned_invoice_template': DEFAULT_SMS_VEHICLE_ASSIGNED_INVOICE_TEMPLATE,
                'sms_vehicle_released_template': DEFAULT_SMS_VEHICLE_RELEASED_TEMPLATE,
        }
        settings_obj = GeneralSettings.objects.filter(tenant=self.request.user.tenant).first()
        if settings_obj is None:
            # GET must remain read-only. Returning the same default shape
            # without persisting it preserves the API while keeping bootstrap
            # creation on an explicit mutation path.
            if self.request.method in {'GET', 'HEAD', 'OPTIONS'}:
                settings_obj = GeneralSettings(tenant=self.request.user.tenant, **defaults)
            else:
                settings_obj = GeneralSettings.objects.create(tenant=self.request.user.tenant, **defaults)
        changed_fields = []
        if not str(settings_obj.sms_provider_base_url or '').strip():
            settings_obj.sms_provider_base_url = 'https://api.iranpayamak.com'
            changed_fields.append('sms_provider_base_url')
        if not str(settings_obj.sms_vehicle_assigned_template or '').strip():
            settings_obj.sms_vehicle_assigned_template = DEFAULT_SMS_VEHICLE_ASSIGNED_TEMPLATE
            changed_fields.append('sms_vehicle_assigned_template')
        assigned_text = str(settings_obj.sms_vehicle_assigned_template or '').strip()
        invoice_text = str(settings_obj.sms_vehicle_assigned_invoice_template or '').strip()
        if invoice_text and '[خلاصه خدمات]' not in assigned_text:
            settings_obj.sms_vehicle_assigned_template = '\n'.join(
                part for part in [assigned_text, invoice_text] if part
            ).strip()
            settings_obj.sms_vehicle_assigned_invoice_template = ''
            changed_fields.extend(['sms_vehicle_assigned_template', 'sms_vehicle_assigned_invoice_template'])
        normalized_assigned_template = normalize_vehicle_assigned_sms_template(
            settings_obj.sms_vehicle_assigned_template
        )
        if settings_obj.sms_vehicle_assigned_template != normalized_assigned_template:
            settings_obj.sms_vehicle_assigned_template = normalized_assigned_template
            changed_fields.append('sms_vehicle_assigned_template')
        normalized_released_template = normalize_vehicle_released_sms_template(
            settings_obj.sms_vehicle_released_template
        )
        if settings_obj.sms_vehicle_released_template != normalized_released_template:
            settings_obj.sms_vehicle_released_template = normalized_released_template
            changed_fields.append('sms_vehicle_released_template')
        if changed_fields and self.request.method not in {'GET', 'HEAD', 'OPTIONS'}:
            changed_fields.append('updated_at')
            settings_obj.save(update_fields=changed_fields)
        return settings_obj
