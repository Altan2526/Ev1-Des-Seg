import re
from itertools import cycle
from django.core.exceptions import ValidationError


def limpiar_y_formatear_rut(rut_raw: str) -> str:
    """Limpia puntos/guiones y devuelve el RUT en formato estándar XX.XXX.XXX-Y."""
    if not rut_raw:
        return ""
    limpio = re.sub(r'[^0-9kK]', '', str(rut_raw)).upper()
    if len(limpio) < 2:
        return limpio
    cuerpo, dv = limpio[:-1], limpio[-1]
    if not cuerpo.isdigit():
        return limpio
    cuerpo_formateado = f"{int(cuerpo):,}".replace(",", ".")
    return f"{cuerpo_formateado}-{dv}"


def validar_rut_chileno(value: str) -> None:
    """Valida matemáticamente un RUT chileno mediante el algoritmo Módulo 11."""
    rut_limpio = re.sub(r'[^0-9kK]', '', str(value)).upper()

    if not re.match(r'^\d{7,8}[0-9K]$', rut_limpio):
        raise ValidationError("El formato del RUT no es válido (Ej: 18.456.789-2).")

    cuerpo = rut_limpio[:-1]
    dv_ingresado = rut_limpio[-1]

    reverso = map(int, reversed(cuerpo))
    factores = cycle(range(2, 8))
    suma = sum(d * f for d, f in zip(reverso, factores))
    resto = 11 - (suma % 11)

    if resto == 11:
        dv_calculado = '0'
    elif resto == 10:
        dv_calculado = 'K'
    else:
        dv_calculado = str(resto)

    if dv_ingresado != dv_calculado:
        raise ValidationError("El RUT ingresado es inválido (dígito verificador incorrecto).")


def limpiar_y_formatear_telefono(telefono_raw: str) -> str:
    """Formatea números móviles o fijos chilenos al estándar +56 X XXXX XXXX."""
    if not telefono_raw:
        return ""
    digitos = re.sub(r'\D', '', str(telefono_raw))
    # Si el usuario escribió el prefijo 56 al inicio, lo separamos de los 9 dígitos
    if digitos.startswith('56') and len(digitos) >= 11:
        digitos = digitos[2:]
    digitos = digitos[:9]
    if len(digitos) == 9:
        return f"+56 {digitos[0]} {digitos[1:5]} {digitos[5:9]}"
    return telefono_raw.strip()


def validar_telefono_chileno(value: str) -> None:
    """Valida que el teléfono cumpla el formato chileno móvil (+56 9) o fijo (+56 2 al 8)."""
    patron = r'^\+56 [2-9] \d{4} \d{4}$'
    if not re.match(patron, str(value)):
        raise ValidationError(
            "Ingrese un teléfono chileno válido: móvil (+56 9 1111 1111) o fijo (+56 2 2111 1111)."
        )