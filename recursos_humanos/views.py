import io
import json
import zipfile
import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_safe, require_POST
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template
from django.utils import timezone
from .models import (
    Empleado, CargaFamiliar, LicenciaMedica, RegistroAuditoria, DocumentoEmitido,
    Concepto, LiquidacionSueldo,
)
from .forms import EmpleadoForm, CargaFamiliarForm, ConceptoForm, LicenciaMedicaForm

URL_LISTA_EMPLEADOS = 'lista_empleados'
URL_DETALLE_EMPLEADO = 'detalle_empleado'

# Datos de la empresa reutilizables (DRY)
DATOS_EMPRESA = {
    'razon_social': 'Mi Empresa SpA',
    'rut': '76.999.888-7',
    'representante_legal': 'Juan Pérez Representante',
    'direccion': 'Av. Providencia 1234, Santiago',
}

# Valores por defecto para documentos
SUELDO_BASE_DEFAULT = 650000
JORNADA_DEFAULT = '40 horas semanales'
CAUSAL_DEFAULT = 'Artículo 161 Inciso 1: Necesidades de la Empresa'


def registrar_log(request, accion: str, entidad: str, detalle: str) -> None:
    """Registra eventos críticos del módulo para trazabilidad y no repudio."""
    ip = request.META.get('REMOTE_ADDR')
    usuario = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
    RegistroAuditoria.objects.create(
        usuario=usuario, accion=accion, entidad=entidad,
        detalle=detalle, ip_origen=ip
    )


def html_to_pdf_bytes(template_src, context_dict):
    """
    Genera el archivo PDF directamente en un búfer de memoria (RAM).
    No guarda copias en el disco ni deja URLs públicas desprotegidas (Mitiga
    Information Disclosure). La importación de xhtml2pdf es perezosa para que
    la aplicación no falle en import-time si el paquete no está disponible.
    """
    try:
        from xhtml2pdf import pisa
    except ImportError:
        return None

    template = get_template(template_src)
    html = template.render(context_dict)
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result)
    if pdf.err:
        return None
    return result.getvalue()


# =====================================================================
# VISTAS DE GESTIÓN DE EMPLEADOS
# =====================================================================

@login_required
@require_safe
def lista_empleados(request):
    """Lista todas las fichas de personal registradas."""
    empleados = Empleado.objects.all().order_by('-creado_en')
    return render(request, 'recursos_humanos/lista_empleados.html', {'empleados': empleados})


@login_required
@require_http_methods(["GET", "POST"])
def crear_empleado(request):
    """Crea una nueva ficha de empleado validando archivos y sanitizando entradas."""
    if request.method == 'POST':
        form = EmpleadoForm(request.POST, request.FILES)
        if form.is_valid():
            empleado = form.save()
            registrar_log(
                request, accion='CREAR', entidad='Ficha de Empleado',
                detalle=f"Se creó la ficha de {empleado.nombre_completo} (RUT: {empleado.rut})."
            )
            messages.success(request, f"Ficha de {empleado.nombre_completo} creada correctamente.")
            return redirect(URL_LISTA_EMPLEADOS)
    else:
        form = EmpleadoForm()
    return render(request, 'recursos_humanos/form_empleado.html', {'form': form, 'accion': 'Crear'})


@login_required
@require_http_methods(["GET", "POST"])
def editar_empleado(request, pk):
    """Actualiza los datos laborales y personales de un empleado existente."""
    empleado = get_object_or_404(Empleado, pk=pk)
    if request.method == 'POST':
        form = EmpleadoForm(request.POST, request.FILES, instance=empleado)
        if form.is_valid():
            empleado = form.save()
            registrar_log(
                request, accion='EDITAR', entidad='Ficha de Empleado',
                detalle=f"Se actualizaron los datos de {empleado.nombre_completo} (RUT: {empleado.rut})."
            )
            messages.success(request, "Datos del empleado actualizados correctamente.")
            return redirect(URL_DETALLE_EMPLEADO, pk=empleado.pk)
    else:
        form = EmpleadoForm(instance=empleado)
    return render(request, 'recursos_humanos/form_empleado.html', {'form': form, 'accion': 'Actualizar'})


@login_required
@require_POST
def eliminar_empleado(request, pk):
    """Elimina de forma segura (vía POST) la ficha de un empleado."""
    empleado = get_object_or_404(Empleado, pk=pk)
    nombre = empleado.nombre_completo
    rut = empleado.rut
    empleado.delete()
    registrar_log(
        request, accion='ELIMINAR', entidad='Ficha de Empleado',
        detalle=f"Se eliminó la ficha del empleado {nombre} (RUT: {rut})."
    )
    messages.warning(request, f"La ficha de {nombre} ({rut}) fue eliminada del sistema.")
    return redirect(URL_LISTA_EMPLEADOS)


@login_required
@require_http_methods(["GET", "POST"])
def detalle_empleado(request, pk):
    """Muestra la ficha completa del empleado y permite agregar cargas familiares."""
    empleado = get_object_or_404(Empleado, pk=pk)
    cargas = empleado.cargas_familiares.all()

    if request.method == 'POST':
        carga_form = CargaFamiliarForm(request.POST)
        if carga_form.is_valid():
            nueva_carga = carga_form.save(commit=False)
            nueva_carga.empleado = empleado
            nueva_carga.save()
            registrar_log(
                request, accion='CREAR', entidad='Carga Familiar',
                detalle=(
                    f"Se registró la carga {nueva_carga.nombre_completo} "
                    f"({nueva_carga.get_parentesco_display()}) para el empleado {empleado.rut}."
                )
            )
            messages.success(request, "Carga familiar registrada correctamente.")
            return redirect(URL_DETALLE_EMPLEADO, pk=empleado.pk)
    else:
        carga_form = CargaFamiliarForm()

    contexto = {'empleado': empleado, 'cargas': cargas, 'carga_form': carga_form}
    return render(request, 'recursos_humanos/detalle_empleado.html', contexto)


@login_required
@require_POST
def eliminar_carga_familiar(request, empleado_pk, carga_pk):
    """Elimina una carga familiar específica vía POST y deja registro en la bitácora."""
    empleado = get_object_or_404(Empleado, pk=empleado_pk)
    carga = get_object_or_404(CargaFamiliar, pk=carga_pk, empleado=empleado)
    nombre_carga = carga.nombre_completo
    carga.delete()
    registrar_log(
        request, accion='ELIMINAR', entidad='Carga Familiar',
        detalle=f"Se eliminó la carga familiar {nombre_carga} asociada al empleado {empleado.rut}."
    )
    messages.warning(request, f"Carga familiar {nombre_carga} eliminada.")
    return redirect(URL_DETALLE_EMPLEADO, pk=empleado.pk)


@login_required
@require_safe
def bitacora_auditoria(request):
    """Muestra los últimos 100 registros de auditoría del sistema."""
    registros = RegistroAuditoria.objects.select_related('usuario').all()[:100]
    return render(request, 'recursos_humanos/bitacora.html', {'registros': registros})


@login_required
@require_safe
def listar_licencias(request):
    """Lista todas las licencias médicas registradas con trazabilidad."""
    licencias = LicenciaMedica.objects.select_related('empleado', 'registrado_por').all()
    return render(request, 'recursos_humanos/listar_licencias.html', {'licencias': licencias})


# =====================================================================
# VISTAS DE GENERACIÓN DE DOCUMENTOS (EV1DS-10)
# =====================================================================

def _parse_int(value, default=0):
    """Convierte un valor a entero con fallback."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _get_parametros_from_post(tipo, empleado, request):
    """Extrae los parámetros del formulario POST según el tipo de documento (valores raw)."""
    if tipo == 'contrato':
        return {
            'tipo_contrato': request.POST.get('tipo_contrato') or empleado.get_tipo_contrato_display(),
            'sueldo_base': _parse_int(request.POST.get('sueldo_base'), SUELDO_BASE_DEFAULT),
            'jornada': request.POST.get('jornada') or JORNADA_DEFAULT,
        }
    else:
        m_anos = _parse_int(request.POST.get('monto_anos'), 0)
        m_aviso = _parse_int(request.POST.get('monto_aviso'), 0)
        m_feriado = _parse_int(request.POST.get('monto_feriado'), 150000)
        m_dias = _parse_int(request.POST.get('monto_pendientes'), 200000)
        total = m_anos + m_aviso + m_feriado + m_dias
        return {
            'fecha_termino': request.POST.get('fecha_termino') or datetime.date.today().isoformat(),
            'causal_termino': request.POST.get('causal') or CAUSAL_DEFAULT,
            'monto_anos_servicio': m_anos,
            'monto_aviso_previo': m_aviso,
            'monto_feriado_proporcional': m_feriado,
            'monto_dias_pendientes': m_dias,
            'total_a_pagar': total,
        }


def _build_pdf_context(tipo, empleado, parametros):
    """Construye el contexto de renderizado para PDF de contrato o finiquito."""
    return {
        'empleado': empleado,
        'empresa': DATOS_EMPRESA,
        'fecha_emision': datetime.date.today(),
        'pdf': True,
        'tipo_doc': tipo,
        'parametros': parametros,
    }


@login_required
@require_safe
def gestion_documentos(request):
    """
    Panel de gestión documental: lista empleados con estado de documentos
    (contrato / finiquito), modales de creación/edición, y histórico de
    documentos emitidos ordenado de más reciente a más antiguo.
    """
    empleados = Empleado.objects.all().order_by('apellido_paterno', 'primer_nombre')

    # Mapa: employee_id -> {'CONTRATO': doc, 'FINIQUITO': doc}
    doc_map = {}
    for doc in DocumentoEmitido.objects.select_related('empleado').filter(
        tipo__in=['CONTRATO', 'FINIQUITO']
    ).order_by('empleado', '-fecha_emision'):
        emp_id = doc.empleado_id
        if emp_id not in doc_map:
            doc_map[emp_id] = {}
        if doc.tipo not in doc_map[emp_id]:
            doc_map[emp_id][doc.tipo] = doc

    documentos = DocumentoEmitido.objects.select_related('empleado').order_by('-fecha_emision')[:50]

    return render(request, 'recursos_humanos/gestion_documentos.html', {
        'empleados': empleados,
        'documentos': documentos,
        'doc_map': doc_map,
        'pdf': False,
    })


@login_required
@require_http_methods(["GET", "POST"])
def registrar_licencia(request):
    """Registra una nueva licencia médica con registro de auditoría."""
    if request.method == 'POST':
        form = LicenciaMedicaForm(request.POST)
        if form.is_valid():
            licencia = form.save(commit=False)
            licencia.registrado_por = request.user  # Mitiga Repudiation (EV1DS-17)
            licencia.save()

            registrar_log(
                request,
                accion='CREAR',
                entidad='Licencia Médica',
                detalle=f"Se registró licencia para {licencia.empleado.nombre_completo} (RUT: {licencia.empleado.rut})."
            )
            messages.success(request, f"Licencia médica para {licencia.empleado.nombre_completo} registrada correctamente.")
            return redirect('listar_licencias')
    else:
        form = LicenciaMedicaForm()
    
    return render(request, 'recursos_humanos/registrar_licencias.html', {'form': form})


# Alias de compatibilidad
registrar_licencias = registrar_licencia
def descargar_documento_individual(request, tipo, empleado_id):
    """
    Emisión individual de Contrato o Finiquito en PDF.

    - POST: crea o modifica el documento. Un trabajador solo tiene un contrato
      y un finiquito vigente; si ya existe, se actualiza (MODIFICACIÓN) en lugar
      de duplicar (CREACIÓN).
    - GET: re-descarga el PDF usando los parámetros ya almacenados.
    """
    tipo = tipo.lower()
    if tipo not in ('contrato', 'finiquito'):
        return JsonResponse(
            {'error': "Tipo de documento no válido. Use 'contrato' o 'finiquito'."}, status=400
        )

    empleado = get_object_or_404(Empleado, pk=empleado_id)
    tipo_db = 'CONTRATO' if tipo == 'contrato' else 'FINIQUITO'

    # Buscar documento existente para este empleado y tipo
    documento_existente = DocumentoEmitido.objects.filter(
        empleado=empleado, tipo=tipo_db
    ).order_by('-fecha_emision').first()

    if request.method == 'GET':
        # Re-descarga del PDF usando parámetros almacenados
        if not documento_existente:
            return JsonResponse(
                {'error': f'No hay {tipo_db.capitalize()} registrado para este empleado.'}, status=404
            )
        parametros = documento_existente.parametros
        contexto = _build_pdf_context(tipo, empleado, parametros)
        pdf_bytes = html_to_pdf_bytes('recursos_humanos/gestion_documentos.html', contexto)
        if not pdf_bytes:
            return JsonResponse({'error': 'Error al generar el archivo PDF.'}, status=500)
        nombre_archivo = f"{tipo.capitalize()}_{empleado.rut}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
        return response

    # POST: crear o modificar
    parametros = _get_parametros_from_post(tipo, empleado, request)

    if documento_existente:
        # MODIFICAR: actualizar registro existente en lugar de duplicar
        documento_existente.parametros = parametros
        documento_existente.emitido_por = request.user
        documento_existente.save()
        registrar_log(
            request, accion='MODIFICAR', entidad=f'{tipo_db.capitalize()} PDF',
            detalle=f"Se modificó el {tipo_db.lower()} de {empleado.nombre_completo} (RUT: {empleado.rut})."
        )
    else:
        # CREAR: nuevo registro
        DocumentoEmitido.objects.create(
            empleado=empleado, tipo=tipo_db,
            parametros=parametros, emitido_por=request.user,
        )
        registrar_log(
            request, accion='CREAR', entidad=f'{tipo_db.capitalize()} PDF',
            detalle=f"Se creó el {tipo_db.lower()} para {empleado.nombre_completo} (RUT: {empleado.rut})."
        )

        # Redirigir a vista previa (descarga PDF opcional desde allí)
        messages.success(
            request,
            f"{tipo_db.capitalize()} de {empleado.nombre_completo} guardado correctamente."
        )
        return redirect('previsualizar_documento', tipo=tipo, empleado_id=empleado.pk)


@login_required
@require_POST
def descargar_documentos_masivos(request):
    """
    Emisión masiva de documentos en un archivo ZIP.
    Espera POST con: tipo ('contrato' o 'finiquito') y empleados_ids (lista).
    Si un empleado ya tiene un documento del tipo indicado, se actualiza;
    si no, se crea.
    """
    try:
        data = json.loads(request.body) if request.body else request.POST
    except (json.JSONDecodeError, TypeError):
        data = request.POST

    tipo = (data.get('tipo', 'contrato') or 'contrato').lower()
    if tipo not in ('contrato', 'finiquito'):
        return JsonResponse({'error': "Tipo de documento no válido."}, status=400)

    empleados_ids = data.get('empleados_ids', [])
    if not empleados_ids:
        return JsonResponse({'error': 'Debe proporcionar una lista de empleados_ids.'}, status=400)

    empleados = Empleado.objects.filter(id__in=empleados_ids)
    if not empleados.exists():
        return JsonResponse({'error': 'No se encontraron empleados con los IDs indicados.'}, status=404)

    tipo_db = 'CONTRATO' if tipo == 'contrato' else 'FINIQUITO'

    zip_buffer = io.BytesIO()
    documentos_creados = 0
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for emp in empleados:
            parametros = _get_parametros_from_post(tipo, emp, request)
            contexto = _build_pdf_context(tipo, emp, parametros)

            pdf_bytes = html_to_pdf_bytes('recursos_humanos/gestion_documentos.html', contexto)
            if pdf_bytes:
                nombre = f"{tipo.capitalize()}_{emp.rut}.pdf"
                zip_file.writestr(nombre, pdf_bytes)
                documentos_creados += 1

                # Crear o actualizar registro de trazabilidad
                doc_existente = DocumentoEmitido.objects.filter(
                    empleado=emp, tipo=tipo_db
                ).order_by('-fecha_emision').first()
                if doc_existente:
                    doc_existente.parametros = parametros
                    doc_existente.emitido_por = request.user
                    doc_existente.save()
                else:
                    DocumentoEmitido.objects.create(
                        empleado=emp, tipo=tipo_db,
                        parametros=parametros, emitido_por=request.user,
                    )

    if not documentos_creados:
        return JsonResponse({'error': 'No se pudo generar ningún documento PDF.'}, status=500)

    registrar_log(
        request, accion='CREAR', entidad=f'{tipo_db.capitalize()}s Masivos',
        detalle=f"Emisión masiva de {tipo_db.lower()}s para {documentos_creados} empleados."
    )

    response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{tipo_db.capitalize()}s_Masivos.zip"'
    return response


# =====================================================================
# VISTAS DE CÁLCULO PARAMÉTRICO DE SUELDOS (EV1DS-06)
# =====================================================================

def _obtener_sueldo_base(empleado):
    """
    Obtiene el sueldo_base y jornada del contrato vigente (EV1DS-10).
    Retorna (sueldo_base, jornada, contrato_doc) o (None, None, None)
    si el empleado no tiene contrato.
    """
    contrato_doc = DocumentoEmitido.objects.filter(
        empleado=empleado, tipo='CONTRATO'
    ).order_by('-fecha_emision').first()
    if not contrato_doc:
        return None, None, None
    parametros = contrato_doc.parametros
    return (
        parametros.get('sueldo_base', 0),
        parametros.get('jornada', ''),
        contrato_doc,
    )


def _validar_entero_positivo(value, field_name='valor'):
    """Valida estrictamente que un valor sea un entero positivo (DevSecOps)."""
    try:
        val = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"El campo '{field_name}' debe ser un número entero.")
    if val < 0:
        raise ValueError(f"El campo '{field_name}' no puede ser negativo.")
    return val


def _calcular_liquidacion(empleado, sueldo_base, periodo, request):
    """
    Ejecuta el cálculo paramétrico de la liquidación de sueldo.
    Obtiene sueldo_base del contrato (EV1DS-10), aplica haberes y
    descuentos activos, y persiste la LiquidacionSueldo.
    Nunca usa eval(); las fórmulas se evalúan con safe_eval_arithmetic().
    """
    contrato_doc = DocumentoEmitido.objects.filter(
        empleado=empleado, tipo='CONTRATO'
    ).order_by('-fecha_emision').first()

    contexto_formula = {'sueldo_base': sueldo_base}

    haberes = {}
    descuentos = {}
    total_haberes = 0
    total_descuentos = 0

    conceptos_activos = Concepto.objects.filter(activo=True)
    for concepto in conceptos_activos:
        valor = concepto.calcular(contexto_formula)
        if valor == 0 and not concepto.formula and concepto.monto_fijo == 0:
            continue
        if concepto.tipo == 'HABER':
            haberes[concepto.nombre] = valor
            total_haberes += valor
        elif concepto.tipo == 'DESCUENTO':
            descuentos[concepto.nombre] = valor
            total_descuentos += valor

    sueldo_liquido = sueldo_base + total_haberes - total_descuentos

    detalle = {
        'sueldo_base': sueldo_base,
        'haberes': haberes,
        'descuentos': descuentos,
        'total_haberes': total_haberes,
        'total_descuentos': total_descuentos,
        'sueldo_liquido': sueldo_liquido,
    }

    liquidacion = LiquidacionSueldo.objects.create(
        empleado=empleado,
        contrato_origen=contrato_doc,
        sueldo_base=sueldo_base,
        total_haberes=total_haberes,
        total_descuentos=total_descuentos,
        sueldo_liquido=sueldo_liquido,
        detalle_conceptos=detalle,
        periodo=periodo,
        emitido_por=request.user,
    )

    registrar_log(
        request, accion='CREAR', entidad='Liquidación de Sueldo',
        detalle=f"Se emitida liquidación para {empleado.nombre_completo} "
                f"(RUT: {empleado.rut}) - Periodo {periodo} - "
                f"Líquido: ${sueldo_liquido:,}."
    )
    return liquidacion


def _build_liquidacion_pdf_context(liquidacion):
    """Construye el contexto de renderizado para el PDF de liquidación."""
    return {
        'liquidacion': liquidacion,
        'empresa': DATOS_EMPRESA,
        'pdf': True,
        'fecha_emision': datetime.date.today(),
    }


@login_required
@require_safe
def calculo_sueldos(request):
    """
    Panel principal de cálculo paramétrico de sueldos (EV1DS-06).

    Muestra:
    - Tabla de conceptos configurados (haberes / descuentos / fórmulas).
    - Tabla de empleados con sueldo_base extraído del contrato vigente
      (EV1DS-10). Botón de cálculo deshabilitado si no hay contrato.
    - Historial de liquidaciones emitidas, ordenado de más reciente a más antiguo.
    """
    # --- Conceptos ---
    haberes = Concepto.objects.filter(tipo='HABER', activo=True).order_by('nombre')
    descuentos = Concepto.objects.filter(tipo='DESCUENTO', activo=True).order_by('nombre')

    # --- Empleados con sueldo_base del contrato vigente (EV1DS-10) ---
    empleados = Empleado.objects.all().order_by('apellido_paterno', 'primer_nombre')
    sueldo_base_map = {}
    jornada_map = {}
    contrato_map = {}
    for emp in empleados:
        sb, jornada, contrato_doc = _obtener_sueldo_base(emp)
        if sb is not None:
            sueldo_base_map[emp.pk] = sb
            jornada_map[emp.pk] = jornada
            contrato_map[emp.pk] = contrato_doc

    # --- Historial de liquidaciones ---
    liquidaciones = LiquidacionSueldo.objects.select_related(
        'empleado', 'contrato_origen'
    ).order_by('-fecha_emision')[:50]

    # --- Concepto form (para el modal de crear/editar) ---
    concepto_form = ConceptoForm()

    # Periodo por defecto: mes/año actual en zona horaria local
    hoy_local = timezone.localtime(timezone.now())
    periodo_default = f"{hoy_local.month:02d}/{hoy_local.year}"

    return render(request, 'recursos_humanos/sueldos.html', {
        'empleados': empleados,
        'sueldo_base_map': sueldo_base_map,
        'jornada_map': jornada_map,
        'contrato_map': contrato_map,
        'haberes': haberes,
        'descuentos': descuentos,
        'conceptos': Concepto.objects.filter(activo=True).order_by('tipo', 'nombre'),
        'liquidaciones': liquidaciones,
        'concepto_form': concepto_form,
        'periodo_default': periodo_default,
    })


@login_required
@require_http_methods(["POST"])
def configurar_concepto(request):
    """
    Crea o actualiza un concepto salarial (haber / descuento / fórmula).
    Valida estrictamente en backend: fórmula segura (AST, nunca eval()),
    montos no negativos.
    """
    pk = request.POST.get('pk')
    if pk:
        try:
            pk_int = int(pk)
            instance = get_object_or_404(Concepto, pk=pk_int)
            form = ConceptoForm(request.POST, instance=instance)
            accion = 'MODIFICAR'
            entidad = 'Concepto Salarial'
        except (ValueError, TypeError):
            return JsonResponse({'error': 'ID de concepto inválido.'}, status=400)
    else:
        form = ConceptoForm(request.POST)
        accion = 'CREAR'
        entidad = 'Concepto Salarial'

    if form.is_valid():
        concepto = form.save()
        registrar_log(
            request, accion=accion, entidad=entidad,
            detalle=f"Concepto {accion.lower()} '{concepto.nombre}' "
                    f"(código: {concepto.codigo}, tipo: {concepto.get_tipo_display()})."
        )
        messages.success(request, f"Concepto '{concepto.nombre}' guardado correctamente.")
        return redirect('calculo_sueldos')
    else:
        errors = {field: [str(e) for e in errors_list] for field, errors_list in form.errors.items()}
        return JsonResponse({'error': 'Validación fallida', 'details': errors}, status=400)


@login_required
@require_POST
def generar_liquidacion(request, empleado_id):
    """
    Calcula y persiste la liquidación de sueldo para un empleado.

    - Obtiene sueldo_base del contrato vigente (EV1DS-10).
    - Si no hay contrato: retorna alerta con enlace a la sección de contratos.
    - Aplica todos los conceptos activos (haberes y descuentos).
    - Registra en la bitácora y genera el PDF en memoria.
    """
    empleado = get_object_or_404(Empleado, pk=empleado_id)
    sueldo_base, jornada, contrato_doc = _obtener_sueldo_base(empleado)

    if sueldo_base is None:
        # Sin contrato vigente: alerta con enlace a EV1DS-10
        alerta = (
            f"El empleado {empleado.nombre_completo} (RUT: {empleado.rut}) "
            "no tiene un contrato vigente emitido. Primero debe emitir su contrato "
            "en Contratos y Finiquitos."
        )
        messages.warning(request, alerta)
        return JsonResponse({
            'sin_contrato': True,
            'alerta': alerta,
            'enlace': '/rrhh/documentos/',
        }, status=400)

    # Validar período
    periodo = request.POST.get('periodo', '')
    if not periodo:
        hoy = timezone.localtime(timezone.now())
        periodo = f"{hoy.month:02d}/{hoy.year}"

    # Validar todos los montos enviados desde el cliente (DevSecOps)
    # El sueldo_base NO viene del cliente; se obtiene del contrato (EV1DS-10)
    try:
        liquidacion = _calcular_liquidacion(empleado, sueldo_base, periodo, request)
    except ValueError as e:
        return JsonResponse({'error': f'Error en el cálculo: {str(e)}'}, status=400)

    # Redirigir a vista previa (descarga PDF opcional desde allí)
    messages.success(
        request,
        f"Liquidación para {empleado.nombre_completo} calculada correctamente."
    )
    return redirect('previsualizar_liquidacion', liquidacion_id=liquidacion.pk)


@login_required
@require_safe
def descargar_liquidacion_pdf(request, liquidacion_id):
    """
    Re-descarga el PDF de una liquidación ya emitida (GET).
    No re-crea ni modifica la liquidación: solo renderiza el PDF
    usando los datos almacenados.
    """
    liquidacion = get_object_or_404(
        LiquidacionSueldo.objects.select_related('empleado', 'contrato_origen'),
        pk=liquidacion_id
    )
    contexto = _build_liquidacion_pdf_context(liquidacion)
    pdf_bytes = html_to_pdf_bytes('recursos_humanos/sueldos.html', contexto)
    if not pdf_bytes:
        return JsonResponse({'error': 'Error al generar el archivo PDF.'}, status=500)

    nombre_archivo = f"Liquidacion_{liquidacion.empleado.rut}_{liquidacion.periodo.replace('/', '-')}.pdf"
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    return response


@login_required
@require_safe
def previsualizar_liquidacion(request, liquidacion_id):
    """
    Vista previa HTML de una liquidación ya calculada.

    El PDF no se descarga automáticamente: el usuario puede revisar los
    cálculos y decidir si descarga el PDF (botón opcional) o vuelve al
    panel de sueldos. El registro ya está persistido, por lo que puede
    descargarlo más tarde desde el historial.
    """
    liquidacion = get_object_or_404(
        LiquidacionSueldo.objects.select_related('empleado', 'contrato_origen'),
        pk=liquidacion_id
    )
    contexto = {
        'preview': True,
        'liquidacion': liquidacion,
        'empresa': DATOS_EMPRESA,
        'fecha_emision': timezone.localtime(timezone.now()).date(),
    }
    return render(request, 'recursos_humanos/sueldos.html', contexto)


@login_required
@require_safe
def previsualizar_documento(request, tipo, empleado_id):
    """
    Vista previa HTML de un contrato o finiquito ya emitido.

    El PDF no se descarga automáticamente: el usuario puede revisar los
    parámetros y decidir si descarga el PDF (botón opcional). El
    documento ya está persistido en la base de datos.
    """
    tipo = tipo.lower()
    if tipo not in ('contrato', 'finiquito'):
        return JsonResponse({'error': "Tipo de documento no válido."}, status=400)
    tipo_db = 'CONTRATO' if tipo == 'contrato' else 'FINIQUITO'
    empleado = get_object_or_404(Empleado, pk=empleado_id)
    documento = DocumentoEmitido.objects.filter(
        empleado=empleado, tipo=tipo_db
    ).order_by('-fecha_emision').first()
    if not documento:
        return JsonResponse(
            {'error': f'No hay {tipo_db.capitalize()} registrado para este empleado.'}, status=404
        )
    contexto = {
        'preview_doc': True,
        'tipo_doc': tipo,
        'parametros': documento.parametros,
        'empleado': empleado,
        'empresa': DATOS_EMPRESA,
        'fecha_emision': documento.fecha_emision,
        'documento': documento,
        'pdf': False,  # NO pdf: vista previa HTML
    }
    return render(request, 'recursos_humanos/gestion_documentos.html', contexto)
