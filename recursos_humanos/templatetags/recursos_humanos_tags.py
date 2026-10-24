"""
Filtros de plantilla para el módulo de Recursos Humanos.
"""
import re
from datetime import datetime
from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def chilean_peso(value):
    """
    Formatea un número como peso chileno con separador de miles por punto:
    650000 -> '650.000'
    Si el valor no es numérico, se devuelve sin cambios.
    """
    if value is None:
        return '0'
    try:
        num = int(value)
        return f"{num:,}".replace(",", ".")
    except (TypeError, ValueError):
        return value


@register.filter
def parse_date(value):
    """
    Parsea una cadena de fecha en formato ISO (YYYY-MM-DD) a un objeto date
    para que pueda ser usado con el filtro |date de Django.
    """
    if not value:
        return value
    if isinstance(value, (datetime, )):
        return value.date() if hasattr(value, 'date') else value
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return value


@register.filter
def get_item(dictionary, key):
    """Obtiene un valor de un diccionario usando una clave variable."""
    if not isinstance(dictionary, dict):
        return None
    return dictionary.get(key)


@register.filter
def localtime(value):
    """Convierte un datetime a la zona horaria local configurada (America/Santiago)."""
    if value is None:
        return value
    try:
        return timezone.localtime(value)
    except (TypeError, ValueError, AttributeError):
        return value


@register.filter
def formatear_rut(rut):
    """Formatea un RUT limpio (184567892) como 18.456.789-2"""
    if not rut:
        return ''
    limpio = re.sub(r'[^0-9kK]', '', str(rut)).upper()
    if len(limpio) < 2:
        return limpio
    cuerpo, dv = limpio[:-1], limpio[-1]
    if not cuerpo.isdigit():
        return limpio
    cuerpo_formateado = f"{int(cuerpo):,}".replace(",", ".")
    return f"{cuerpo_formateado}-{dv}"
