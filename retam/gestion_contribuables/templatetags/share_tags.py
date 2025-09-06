from django import template
from urllib.parse import quote_plus
import re
from django.conf import settings

register = template.Library()

def _normalize_phone(phone):
    if not phone:
        return None
    s = str(phone).strip()
    digits = re.sub(r'\D+', '', s)
    if digits.startswith('00'):
        digits = digits[2:]
    if digits.startswith('0'):
        default_cc = getattr(settings, 'DEFAULT_PHONE_COUNTRY_CODE', '')
        if default_cc:
            digits = default_cc + digits.lstrip('0')
    return digits or None

@register.simple_tag
def whatsapp_url(phone, url, reference=''):
    """Retourne wa.me/<phone>?text=... ou wa.me/?text=..."""
    phone_normal = _normalize_phone(phone)
    msg = f"Quittance paiement {reference} : {url}"
    if phone_normal:
        return f"https://wa.me/{phone_normal}?text=" + quote_plus(msg)
    return "https://wa.me/?text=" + quote_plus(msg)