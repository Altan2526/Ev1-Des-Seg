import re
from django.core.exceptions import ValidationError

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


MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB por archivo


def validar_mime_real(archivo, formatos_permitidos: tuple):
    """
    EV1DS-38 (CWE-434): Valida el tamaño máximo y la firma binaria real
    (Magic Bytes) del archivo subido, independientemente de su extensión o Content-Type.
    """
    if not archivo:
        return

    if getattr(archivo, 'size', 0) > MAX_UPLOAD_BYTES:
        raise ValidationError("El archivo excede el tamaño máximo permitido de 5 MB.")

    pos = archivo.tell()
    header = archivo.read(16)
    archivo.seek(pos)

    firmas_magicas = {
        'pdf': header.startswith(b'%PDF-'),
        'jpg': header.startswith(b'\xff\xd8\xff'),
        'jpeg': header.startswith(b'\xff\xd8\xff'),
        'png': header.startswith(b'\x89PNG\r\n\x1a\n'),
    }

    if not any(firmas_magicas.get(fmt, False) for fmt in formatos_permitidos):
        raise ValidationError(
            f"El contenido binario del archivo no corresponde a un formato válido "
            f"({', '.join(fmt.upper() for fmt in formatos_permitidos)})."
        )

def sanitizar_directivas_ssi(valor: str) -> str:
    """
    EV1DS-41 (CWE-97): Neutraliza cualquier intento de inyección de directivas
    Server-Side Include (<!--#exec, <!--#include, etc.) antes de renderizar HTML/PDF.
    """
    if valor is None:
        return ""
    texto = str(valor)
    return re.sub(r'<!--\s*#', '&lt;!--#', texto, flags=re.IGNORECASE)


def extraer_ids_enteros_positivos(lista_raw) -> list[int]:
    """
    EV1DS-41 (CWE-20 / CWE-97): Filtra y valida estrictamente una lista de IDs
    enviados por POST/GET. Si alguno contiene texto malicioso o SSI, lanza ValueError.
    """
    if not lista_raw:
        return []
    ids_limpios = []
    for item in lista_raw:
        cadena = str(item).strip()
        if not cadena.isdigit():
            raise ValueError(f"Identificador inválido detectado: '{sanitizar_texto_log(cadena, 40)}'")
        numero = int(cadena)
        if numero <= 0:
            raise ValueError("Los identificadores deben ser enteros positivos.")
        ids_limpios.append(numero)
    return ids_limpios