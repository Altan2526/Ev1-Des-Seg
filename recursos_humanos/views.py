from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_safe, require_POST
from django.contrib import messages
from .models import Empleado, CargaFamiliar, RegistroAuditoria
from .forms import EmpleadoForm, CargaFamiliarForm

URL_LISTA_EMPLEADOS = 'lista_empleados'
URL_DETALLE_EMPLEADO = 'detalle_empleado'


def registrar_log(request, accion: str, entidad: str, detalle: str) -> None:
    """Registra eventos críticos del módulo para trazabilidad y no repudio (STRIDE)."""
    ip = request.META.get('REMOTE_ADDR')
    RegistroAuditoria.objects.create(
        usuario=request.user if request.user.is_authenticated else None,
        accion=accion,
        entidad=entidad,
        detalle=detalle,
        ip_origen=ip
    )


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