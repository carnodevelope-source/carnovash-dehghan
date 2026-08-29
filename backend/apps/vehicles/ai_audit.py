import base64
import json
import logging
import re
import threading
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.db import transaction
from django.utils import timezone


logger = logging.getLogger(__name__)


def _value(source, key, default=''):
    if hasattr(source, 'get'):
        return source.get(key, default)
    return default


def _clean_text(value):
    return str(value or '').strip()


def _safe_filename_part(value):
    cleaned = re.sub(r'[^A-Za-z0-9_-]+', '-', str(value or '').strip())
    return cleaned.strip('-')[:80] or 'plate'


def _decode_data_url(value):
    raw = _clean_text(value)
    if not raw:
        return b'', 'jpg'

    header = ''
    payload = raw
    if raw.startswith('data:') and ',' in raw:
        header, payload = raw.split(',', 1)

    extension = 'jpg'
    if 'png' in header:
        extension = 'png'
    elif 'webp' in header:
        extension = 'webp'
    elif 'jpeg' in header or 'jpg' in header:
        extension = 'jpg'

    return base64.b64decode(payload), extension


def _vehicle_car_model(vehicle, request_data=None):
    return (
        _clean_text(getattr(vehicle, 'car_model', ''))
        or _clean_text(_value(request_data or {}, 'car_model'))
        or _clean_text(_value(request_data or {}, 'model'))
    )


def _vehicle_car_color(vehicle, request_data=None):
    return (
        _clean_text(getattr(vehicle, 'car_color', ''))
        or _clean_text(_value(request_data or {}, 'car_color'))
        or _clean_text(_value(request_data or {}, 'color'))
    )


def _save_ai_image(*, vehicle, request_data, record):
    image_base64 = _value(request_data, 'ai_image_base64') or _value(request_data, 'image_base64')
    image_bytes, extension = _decode_data_url(image_base64)
    if not image_bytes:
        return ''

    now = timezone.localtime()
    relative_dir = Path('ai_plate_audit') / now.strftime('%Y') / now.strftime('%m') / now.strftime('%d')
    media_root = Path(settings.MEDIA_ROOT)
    target_dir = media_root / relative_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    plate_part = _safe_filename_part(getattr(vehicle, 'plate_number', '') or getattr(vehicle, 'id', ''))
    model_part = _safe_filename_part(record.get('car_model') or 'model')
    color_part = _safe_filename_part(record.get('car_color') or 'color')
    stem = f'vehicle-{vehicle.id}-{plate_part}-{model_part}-{color_part}-{uuid4().hex[:10]}'
    relative_path = relative_dir / f'{stem}.{extension}'
    absolute_path = media_root / relative_path
    absolute_path.write_bytes(image_bytes)

    sidecar_path = absolute_path.with_suffix('.json')
    sidecar_payload = {
        **record,
        'image_path': relative_path.as_posix(),
    }
    sidecar_path.write_text(json.dumps(sidecar_payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return relative_path.as_posix()


def _converted_plate_from_request(request_data):
    converted = _clean_text(_value(request_data, 'ai_converted_plate'))
    if converted:
        return converted

    left = _clean_text(_value(request_data, 'ai_converted_plate_left'))
    letter = _clean_text(_value(request_data, 'ai_converted_plate_letter'))
    mid = _clean_text(_value(request_data, 'ai_converted_plate_mid'))
    right = _clean_text(_value(request_data, 'ai_converted_plate_right'))
    plate_type = _clean_text(_value(request_data, 'ai_converted_plate_type') or _value(request_data, 'plate_type'))
    if plate_type == 'motorcycle':
        return ' '.join(part for part in [mid, letter] if part)
    return ' '.join(part for part in [left, letter, mid, right] if part)


def _final_plate_from_vehicle(vehicle):
    plate_type = _clean_text(getattr(vehicle, 'plate_type', ''))
    if plate_type == 'motorcycle':
        return ' '.join(part for part in [
            _clean_text(getattr(vehicle, 'plate_mid', '')),
            _clean_text(getattr(vehicle, 'plate_letter', '')),
        ] if part) or _clean_text(getattr(vehicle, 'plate_number', ''))
    return ' '.join(part for part in [
        _clean_text(getattr(vehicle, 'plate_left', '')),
        _clean_text(getattr(vehicle, 'plate_letter', '')),
        _clean_text(getattr(vehicle, 'plate_mid', '')),
        _clean_text(getattr(vehicle, 'plate_right', '')),
    ] if part) or _clean_text(getattr(vehicle, 'plate_number', ''))


def log_ai_plate_audit_event(*, vehicle, request, operation):
    request_data = getattr(request, 'data', {}) or {}
    # Snapshot mutable request payload before any deferred write so the worker
    # thread never touches a closed request cycle.
    if hasattr(request_data, 'copy'):
        try:
            request_data = request_data.copy()
        except Exception:
            request_data = dict(request_data) if hasattr(request_data, 'items') else {}
    elif hasattr(request_data, 'items'):
        request_data = dict(request_data)

    raw_text = _clean_text(_value(request_data, 'ai_raw_text'))
    persian_text = _clean_text(_value(request_data, 'ai_persian_text'))
    converted_plate = _converted_plate_from_request(request_data)
    has_image = bool(_value(request_data, 'ai_image_base64') or _value(request_data, 'image_base64'))
    car_model = _vehicle_car_model(vehicle, request_data)
    car_color = _vehicle_car_color(vehicle, request_data)

    # Every admission (create) must be logged with plate + model + color.
    # Updates still log when AI payload exists, or when model/color/plate are present.
    if operation != 'create' and not any([raw_text, persian_text, converted_plate, has_image, car_model, car_color]):
        return

    user = getattr(request, 'user', None)
    tenant = getattr(user, 'tenant', None)
    vehicle_id = getattr(vehicle, 'id', None)
    plate_number = getattr(vehicle, 'plate_number', '')
    plate_type = _clean_text(getattr(vehicle, 'plate_type', ''))
    plate_mid = _clean_text(getattr(vehicle, 'plate_mid', ''))
    plate_letter = _clean_text(getattr(vehicle, 'plate_letter', ''))
    plate_left = _clean_text(getattr(vehicle, 'plate_left', ''))
    plate_right = _clean_text(getattr(vehicle, 'plate_right', ''))
    operator_id = getattr(user, 'id', None) if getattr(user, 'is_authenticated', False) else None
    tenant_id = getattr(tenant, 'id', None)

    def _write_audit():
        try:
            now = timezone.localtime()
            # Rebuild a lightweight vehicle-like namespace for helpers that need fields.
            class _VehicleSnap:
                id = vehicle_id
                plate_number = plate_number
                plate_type = plate_type
                plate_mid = plate_mid
                plate_letter = plate_letter
                plate_left = plate_left
                plate_right = plate_right
                car_model = car_model
                car_color = car_color

            snap = _VehicleSnap()
            record = {
                'created_at': now.isoformat(),
                'operation': operation,
                'tenant_id': tenant_id,
                'vehicle_id': vehicle_id,
                'operator_id': operator_id,
                'ai_session_id': _clean_text(_value(request_data, 'ai_session_id')),
                'ai_raw_text': raw_text,
                'ai_persian_text': persian_text,
                'ai_converted_plate': converted_plate,
                'final_plate': _final_plate_from_vehicle(snap),
                'plate_type': plate_type,
                'car_model': car_model,
                'car_color': car_color,
                'ai_confidence': _value(request_data, 'ai_confidence', None),
                'ai_latency_ms': _value(request_data, 'ai_latency_ms', None),
                'image_path': '',
            }

            image_path = _save_ai_image(vehicle=snap, request_data=request_data, record=record)
            record['image_path'] = image_path

            log_dir = Path(settings.MEDIA_ROOT) / 'ai_plate_audit'
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / 'plate_recognition_audit.jsonl'
            with log_path.open('a', encoding='utf-8') as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + '\n')
        except Exception:
            logger.exception('Failed to write AI plate audit log for vehicle %s', vehicle_id)

    # Image decode + disk write must never stall the admission HTTP response.
    if has_image:
        transaction.on_commit(lambda: threading.Thread(target=_write_audit, daemon=True).start())
    else:
        _write_audit()
