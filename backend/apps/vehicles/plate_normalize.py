"""Canonical Iranian plate normalization shared by lookup, loyalty, and intake."""

from __future__ import annotations

_DIGIT_TRANSLATION = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')

_ENGLISH_LETTER_MAP = {
    'a': 'الف',
    'b': 'ب',
    'c': 'ص',
    'd': 'د',
    'e': 'ه',
    'f': 'ف',
    'g': 'گ',
    'h': 'ح',
    'i': 'ی',
    'j': 'ج',
    'k': 'ک',
    'l': 'ل',
    'm': 'م',
    'n': 'ن',
    'o': 'و',
    'p': 'پ',
    'q': 'ق',
    'r': 'ر',
    's': 'س',
    't': 'ط',
    'u': 'ع',
    'v': 'و',
    'w': 'و',
    'x': 'ش',
    'y': 'ی',
    'z': 'ز',
}

_PERSIAN_LETTER_MAP = {
    'ا': 'الف',
    'آ': 'الف',
    'الف': 'الف',
    'ب': 'ب',
    'پ': 'پ',
    'ت': 'ت',
    'ث': 'ث',
    'ج': 'ج',
    'چ': 'چ',
    'ح': 'ح',
    'خ': 'خ',
    'د': 'د',
    'ذ': 'ذ',
    'ر': 'ر',
    'ز': 'ز',
    'ژ': 'ژ',
    'س': 'س',
    'ش': 'ش',
    'ص': 'ص',
    'ض': 'ض',
    'ط': 'ط',
    'ظ': 'ظ',
    'ع': 'ع',
    'غ': 'غ',
    'ف': 'ف',
    'ق': 'ق',
    'ک': 'ک',
    'ك': 'ک',
    'گ': 'گ',
    'ل': 'ل',
    'م': 'م',
    'ن': 'ن',
    'و': 'و',
    'ه': 'ه',
    'ی': 'ی',
    'ي': 'ی',
}


def normalize_digits(value=''):
    return str(value or '').translate(_DIGIT_TRANSLATION)


def normalize_plate_letter(value=''):
    raw = str(value or '').replace('\u200c', '').replace(' ', '').strip()
    if not raw:
        return ''
    token = raw[:3]
    if token in _PERSIAN_LETTER_MAP:
        return _PERSIAN_LETTER_MAP[token]
    lower = raw[:1].lower()
    if lower in _ENGLISH_LETTER_MAP:
        return _ENGLISH_LETTER_MAP[lower]
    first = raw[:1]
    return _PERSIAN_LETTER_MAP.get(first, '')


def plate_letter_lookup_variants(value=''):
    """Return equivalent letter forms for legacy rows (ا vs الف, latin, etc.)."""
    normalized = normalize_plate_letter(value)
    variants = set()
    raw = str(value or '').replace('\u200c', '').replace(' ', '').strip()
    if raw:
        variants.add(raw)
    if normalized:
        variants.add(normalized)
        if normalized == 'الف':
            variants.update({'ا', 'آ', 'الف', 'A', 'a'})
        else:
            for latin, persian in _ENGLISH_LETTER_MAP.items():
                if persian == normalized:
                    variants.add(latin)
                    variants.add(latin.upper())
    return [item for item in variants if item]


def normalize_plate_parts(
    *,
    plate_number='',
    plate_left='',
    plate_letter='',
    plate_mid='',
    plate_right='',
    plate_type='car',
):
    plate_type_value = str(plate_type or 'car').strip().lower() or 'car'
    left = normalize_digits(plate_left).strip()
    mid = normalize_digits(plate_mid).strip()
    right = normalize_digits(plate_right).strip()
    letter_raw = str(plate_letter or '').strip()

    if plate_type_value == 'motorcycle':
        mid = ''.join(ch for ch in normalize_digits(mid) if ch.isdigit())[:3]
        letter = ''.join(ch for ch in normalize_digits(letter_raw) if ch.isdigit())[:5]
        left = ''
        right = ''
        plate = f'{mid} {letter}'.strip() if mid and letter else normalize_digits(plate_number).strip()
        return {
            'plate_left': '',
            'plate_letter': letter,
            'plate_mid': mid,
            'plate_right': '',
            'plate_number': plate,
            'plate_type': plate_type_value,
        }

    letter = normalize_plate_letter(letter_raw)
    left = ''.join(ch for ch in left if ch.isdigit())[:2]
    mid = ''.join(ch for ch in mid if ch.isdigit())[:3]
    right = ''.join(ch for ch in right if ch.isdigit())[:2]

    if left and letter and mid and right:
        plate = f'{left} {letter} {mid} {right}'
    else:
        raw = normalize_digits(plate_number).strip()
        parts = [part for part in raw.split() if part]
        if len(parts) >= 4:
            left = ''.join(ch for ch in normalize_digits(parts[0]) if ch.isdigit())[:2] or left
            letter = normalize_plate_letter(parts[1]) or letter
            mid = ''.join(ch for ch in normalize_digits(parts[2]) if ch.isdigit())[:3] or mid
            right = ''.join(ch for ch in normalize_digits(parts[3]) if ch.isdigit())[:2] or right
            if left and letter and mid and right:
                plate = f'{left} {letter} {mid} {right}'
            else:
                plate = raw
        else:
            plate = raw

    return {
        'plate_left': left,
        'plate_letter': letter,
        'plate_mid': mid,
        'plate_right': right,
        'plate_number': plate,
        'plate_type': plate_type_value,
    }


def build_plate_number_from_parts(*, plate_left='', plate_letter='', plate_mid='', plate_right='', plate_type='car'):
    parts = normalize_plate_parts(
        plate_left=plate_left,
        plate_letter=plate_letter,
        plate_mid=plate_mid,
        plate_right=plate_right,
        plate_type=plate_type,
    )
    return parts['plate_number']
