import re


def sanitizar_texto_log(valor: str, max_len: int = 400) -> str:
    """
    EV1DS-35 (CWE-117): Neutraliza saltos de línea (\r, \n), tabulaciones y
    caracteres de control ASCII para prevenir Log Injection / Log Forging.
    """
    if valor is None:
        return ""
    texto = str(valor)
    # Reemplazar cualquier salto de línea o carácter de control por un espacio simple
    limpio = re.sub(r'[\r\n\t\x00-\x1f\x7f]+', ' ', texto)
    return limpio.strip()[:max_len]


def enmascarar_rut_log(rut: str) -> str:
    """
    Enmascara los dígitos centrales del RUT antes de escribirlo en bitácora
    ('12.345.678-9' -> '12..-9') para cumplir minimización de PII.
    """
    if not rut:
        return ""
    limpio = sanitizar_texto_log(rut, 20)
    if '-' in limpio:
        cuerpo, dv = limpio.rsplit('-', 1)
        prefijo = cuerpo[:2] if len(cuerpo) >= 2 else ""
        return f"{prefijo}.**.-{dv}"
    return f"{limpio[:2]}"