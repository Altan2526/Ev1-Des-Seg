import io
import json
import zipfile
import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_safe, require_POST
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template
from django.conf import settings
from xhtml2pdf import pisa

from .models import Empleado, CargaFamiliar, RegistroAuditoria, DocumentoEmitido
from .forms import EmpleadoForm, CargaFamiliarForm

# Soporte para validar Token JWT
try:
    from rest_framework_simplejwt.authentication import JWTAuthentication
    HAS_SIMPLE_JWT = True
except ImportError:
    import jwt
    HAS_SIMPLE_JWT = False

URL_LISTA_EMPLEADOS = 'lista_empleados'
URL_DETALLE_EMPLEADO = 'detalle_empleado'


def registrar_log(request, accion: str, entidad: str, detalle: str) -> None:
    """Registra eventos críticos del módulo para trazabilidad y no repudio (STRIDE)."""
    ip = request.META.get('REMOTE_ADDR')
    usuario = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
    RegistroAuditoria.objects.create(
        usuario=usuario,
        accion=accion,
        entidad=entidad,
        detalle=detalle,
        ip_origen=ip
    )


# =====================================================================
# FUNCIONES AUXILIARES DE SEGURIDAD (MITIGACIÓN STRIDE)
# =====================================================================

def verificar_autenticacion_jwt_admin(request):
    """
    SEGURIDAD: Mitigación Elevation of Privilege.
    Verifica que la solicitud cuente con un Token JWT válido o sesión administrativa
    y que el usuario posea atributos administrativos (is_staff).
    """
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Bearer '):
        # Permite acceso si el usuario ya está autenticado en la sesión web como staff
        if request.user.is_authenticated and request.user.is_staff:
            return request.user, None
        return None, JsonResponse(
            {'error': 'Autenticación requerida. Proporcione un token JWT válido (Bearer <token>).'},
            status=401
        )

    token_str = auth_header.split(' ')[1]

    try:
        if HAS_SIMPLE_JWT:
            jwt_auth = JWTAuthentication()
            validated_token = jwt_auth.get_validated_token(token_str)
            user = jwt_auth.get_user(validated_token)
        else:
            payload = jwt.decode(token_str, settings.SECRET_KEY, algorithms=['HS256'])
            user = User.objects.get(id=payload.get('user_id', payload.get('id')))
    except Exception as e:
        return None, JsonResponse({'error': f'Token JWT inválido o expirado: {str(e)}'}, status=401)

    # Validar que sea administrador o analista con permisos (is_staff)
    if not user.is_staff:
        return None, JsonResponse(
            {'error': 'Acceso denegado: Se requieren privilegios de analista de Recursos Humanos.'},
            status=403
        )

    return user, None


def html_to_pdf_bytes(template_src, context_dict={}):
    """
    SEGURIDAD: Mitigación Information Disclosure.
    Genera el archivo PDF directamente en un búfer de memoria (RAM).
    No guarda copias en el disco ni deja URLs públicas desprotegidas.
    """
    template = get_template(template_src)
    html = template.render(context_dict)
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return result.getvalue()
    return None


# =====================================================================
# VISTAS EXISTENTES DE GESTIÓN DE EMPLEADOS (INTACTAS)
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
                request,
                accion='CREAR',
                entidad='Ficha de Empleado',
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
                request,
                accion='EDITAR',
                entidad='Ficha de Empleado',
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
    """Elimina de forma segura (vía POST) la ficha de un empleado y registra la auditoría."""
    empleado = get_object_or_404(Empleado, pk=pk)
    nombre = empleado.nombre_completo
    rut = empleado.rut
    empleado.delete()
    registrar_log(
        request,
        accion='ELIMINAR',
        entidad='Ficha de Empleado',
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
                request,
                accion='CREAR',
                entidad='Carga Familiar',
                detalle=(
                    f"Se registró la carga {nueva_carga.nombre_completo} "
                    f"({nueva_carga.get_parentesco_display()}) para el empleado {empleado.rut}."
                )
            )
            messages.success(request, "Carga familiar registrada correctamente.")
            return redirect(URL_DETALLE_EMPLEADO, pk=empleado.pk)
    else:
        carga_form = CargaFamiliarForm()

    contexto = {
        'empleado': empleado,
        'cargas': cargas,
        'carga_form': carga_form
    }
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
        request,
        accion='ELIMINAR',
        entidad='Carga Familiar',
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


# =====================================================================
# VISTAS DE GENERACIÓN DE DOCUMENTOS (CONECTADAS A LOS MODALES)
# =====================================================================

def descargar_documento_individual(request, tipo, empleado_id):
    """
    Subtarea 2 y 3: Emisión individual de Contrato o Finiquito.
    Recibe la causal de despido, fechas, sueldo y montos desde las ventanitas modales.
    """
    usuario, error = verificar_autenticacion_jwt_admin(request)
    if error:
        return error

    tipo = tipo.lower()
    if tipo not in ['contrato', 'finiquito']:
        return JsonResponse({'error': "Tipo de documento no válido. Use 'contrato' o 'finiquito'."}, status=400)

    empleado = get_object_or_404(Empleado, pk=empleado_id)

    datos_empresa = {
        'razon_social': 'Mi Empresa SpA',
        'rut': '76.999.888-7',
        'representante_legal': 'Juan Pérez Representante',
        'direccion': 'Av. Providencia 1234, Santiago',
    }

    if tipo == 'contrato':
        # Captura lo enviado desde el modal de contrato (o usa valores por defecto si entra por GET)
        tipo_contrato = request.POST.get('tipo_contrato') or empleado.get_tipo_contrato_display()
        sueldo_val = request.POST.get('sueldo_base') or 650000
        sueldo_fmt = f"{int(sueldo_val):,}".replace(",", ".")
        jornada = request.POST.get('jornada') or "40 horas semanales"

        template_name = 'recursos_humanos/contrato_pdf.html'
        contexto = {
            'empleado': empleado,
            'colaborador': empleado,
            'empresa': datos_empresa,
            'fecha_emision': datetime.date.today(),
            'contrato_datos': {
                'tipo': tipo_contrato,
                'sueldo_base': sueldo_fmt,
                'jornada': jornada,
            }
        }
        tipo_db = 'CONTRATO'
        nombre_archivo = f"Contrato_{empleado.rut}.pdf"
        detalle_log = f"Emisión de contrato ({tipo_contrato}) para {empleado.nombre_completo} (RUT: {empleado.rut})."

    else:
        # Captura la causal de despido y los montos enviados desde el modal de finiquito
        causal = request.POST.get('causal') or 'Artículo 161 Inciso 1: Necesidades de la Empresa'
        fecha_termino = request.POST.get('fecha_termino') or datetime.date.today()

        m_anos = int(request.POST.get('monto_anos') or 0)
        m_aviso = int(request.POST.get('monto_aviso') or 0)
        m_feriado = int(request.POST.get('monto_feriado') or 150000)
        m_dias = int(request.POST.get('monto_pendientes') or 200000)
        total = m_anos + m_aviso + m_feriado + m_dias

        template_name = 'recursos_humanos/finiquito_pdf.html'
        contexto = {
            'empleado': empleado,
            'colaborador': empleado,
            'empresa': datos_empresa,
            'fecha_emision': datetime.date.today(),
            'finiquito': {
                'fecha_termino': fecha_termino,
                'causal_termino': causal,
                'monto_anos_servicio': f"{m_anos:,}".replace(",", "."),
                'monto_aviso_previo': f"{m_aviso:,}".replace(",", "."),
                'monto_feriado_proporcional': f"{m_feriado:,}".replace(",", "."),
                'monto_dias_pendientes': f"{m_dias:,}".replace(",", "."),
                'total_a_pagar': f"{total:,}".replace(",", "."),
            }
        }
        tipo_db = 'FINIQUITO'
        nombre_archivo = f"Finiquito_{empleado.rut}.pdf"
        detalle_log = f"Finiquito emitido para {empleado.nombre_completo} (Causal: {causal})."

    # Generación segura en memoria RAM (Mitiga Information Disclosure)
    pdf_bytes = html_to_pdf_bytes(template_name, contexto)
    if not pdf_bytes:
        return JsonResponse({'error': 'Error al renderizar el archivo PDF.'}, status=500)

    # Registro en auditoría
    try:
        DocumentoEmitido.objects.create(
            empleado=empleado,
            tipo=tipo_db,
            emitido_por=usuario
        )
    except Exception:
        pass

    registrar_log(
        request,
        accion='CREAR',
        entidad=f'{tipo_db.capitalize()} PDF',
        detalle=detalle_log
    )

    # Descarga directa sin persistir en disco
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    return response


@require_http_methods(["POST"])
def descargar_documentos_masivos(request):
    """
    Subtarea 2 y 3: Emisión masiva de documentos en un archivo ZIP.
    Espera POST con: tipo ('contrato' o 'finiquito') y empleados_ids (lista de IDs).
    """
    usuario, error = verificar_autenticacion_jwt_admin(request)
    if error:
        return error

    try:
        data = json.loads(request.body) if request.body else request.POST
    except Exception:
        data = request.POST

    tipo = data.get('tipo', 'contrato').lower()
    empleados_ids = data.get('empleados_ids', [])

    if not empleados_ids:
        return JsonResponse({'error': 'Debe proporcionar una lista de empleados_ids.'}, status=400)

    empleados = Empleado.objects.filter(id__in=empleados_ids)
    if not empleados.exists():
        return JsonResponse({'error': 'No se encontraron empleados con los IDs indicados.'}, status=404)

    template_name = 'recursos_humanos/contrato_pdf.html' if tipo == 'contrato' else 'recursos_humanos/finiquito_pdf.html'
    tipo_db = 'CONTRATO' if tipo == 'contrato' else 'FINIQUITO'

    datos_empresa = {
        'razon_social': 'Mi Empresa SpA',
        'rut': '76.999.888-7',
        'representante_legal': 'Juan Pérez Representante',
        'direccion': 'Av. Providencia 1234, Santiago',
    }

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for emp in empleados:
            contexto = {
                'empleado': emp,
                'colaborador': emp,
                'empresa': datos_empresa,
                'fecha_emision': datetime.date.today(),
            }
            if tipo == 'finiquito':
                contexto['finiquito'] = {
                    'fecha_termino': datetime.date.today(),
                    'causal_termino': 'Conclusión de los servicios pactados',
                    'monto_anos_servicio': '0',
                    'monto_aviso_previo': '0',
                    'monto_feriado_proporcional': '120.000',
                    'monto_dias_pendientes': '180.000',
                    'total_a_pagar': '300.000',
                }

            pdf_bytes = html_to_pdf_bytes(template_name, contexto)
            if pdf_bytes:
                zip_file.writestr(f"{tipo.capitalize()}_{emp.rut}.pdf", pdf_bytes)
                try:
                    DocumentoEmitido.objects.create(
                        empleado=emp,
                        tipo=tipo_db,
                        emitido_por=usuario
                    )
                except Exception:
                    pass

    registrar_log(
        request,
        accion='CREAR',
        entidad=f'{tipo_db.capitalize()}s Masivos',
        detalle=f"Emisión masiva de {tipo_db.lower()}s para {len(empleados)} empleados."
    )

    response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{tipo.capitalize()}s_Masivos.zip"'
    return response


# =====================================================================
# VISTA DEL PANEL (OPCIONAL)
# =====================================================================

@login_required
@require_safe
def panel_documentos(request):
    """Muestra la vista de gestión si se ingresa a la URL directa."""
    empleados = Empleado.objects.all().order_by('apellido_paterno')
    return render(request, 'recursos_humanos/lista_empleados.html', {'empleados': empleados})



@login_required
@require_safe
def panel_documentos(request):
    """Muestra la pantalla exclusiva de Contratos y Finiquitos."""
    empleados = Empleado.objects.all().order_by('apellido_paterno')
    return render(request, 'recursos_humanos/gestion_documentos.html', {'empleados': empleados})