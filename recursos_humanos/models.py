from django.db import models, transaction
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.contrib.auth.models import User
from .validators import validar_rut_chileno


class Empleado(models.Model):
    PREVISION_CHOICES = [
        ('FONASA', 'Fonasa'),
        ('ISAPRE', 'Isapre'),
    ]
    TIPO_CONTRATO_CHOICES = [
        ('INDEFINIDO', 'Plazo Indefinido'),
        ('PLAZO_FIJO', 'Plazo Fijo'),
        ('POR_OBRA', 'Por Obra o Faena'),
    ]
    CENTRO_COSTO_CHOICES = [
        ('CC-100', 'Administración y Finanzas'),
        ('CC-200', 'Recursos Humanos'),
        ('CC-300', 'Operaciones y Terreno'),
        ('CC-400', 'Bodega e Inventario'),
        ('CC-500', 'Ventas y Comercial'),
        ('CC-600', 'Tecnologías de la Información (TI)'),
    ]
    AFP_CHOICES = [
        ('CAPITAL', 'AFP Capital'),
        ('CUPRUM', 'AFP Cuprum'),
        ('HABITAT', 'AFP Habitat'),
        ('MODELO', 'AFP Modelo'),
        ('PLANVITAL', 'AFP PlanVital'),
        ('PROVIDA', 'AFP ProVida'),
        ('UNO', 'AFP Uno'),
    ]

    # Datos Personales
    rut = models.CharField(
        max_length=12, unique=True,
        validators=[validar_rut_chileno], verbose_name="RUT"
    )
    primer_nombre = models.CharField(max_length=50, verbose_name="Primer Nombre")
    segundo_nombre = models.CharField(
        max_length=50, blank=True, default='',
        verbose_name="Segundo Nombre (Opcional)"
    )
    apellido_paterno = models.CharField(max_length=50, verbose_name="Apellido Paterno")
    apellido_materno = models.CharField(max_length=50, verbose_name="Apellido Materno")
    fecha_nacimiento = models.DateField(verbose_name="Fecha de Nacimiento")
    direccion = models.CharField(max_length=255, verbose_name="Dirección Particular")
    telefono = models.CharField(max_length=20, verbose_name="Teléfono")
    email = models.EmailField(unique=True, verbose_name="Correo Electrónico")

    # Datos Laborales
    cargo = models.CharField(max_length=100, verbose_name="Cargo")
    centro_costo = models.CharField(
        max_length=10, choices=CENTRO_COSTO_CHOICES,
        verbose_name="Departamento / Centro de Costo"
    )
    tipo_contrato = models.CharField(
        max_length=20, choices=TIPO_CONTRATO_CHOICES,
        default='INDEFINIDO', verbose_name="Tipo de Contrato"
    )
    fecha_ingreso = models.DateField(verbose_name="Fecha de Ingreso")
    prevision = models.CharField(
        max_length=20, choices=PREVISION_CHOICES,
        default='FONASA', verbose_name="Previsión de Salud"
    )
    afp = models.CharField(
        max_length=20, choices=AFP_CHOICES, verbose_name="AFP"
    )
    codigo_reloj_control = models.CharField(
        max_length=20, unique=True, editable=False,
        verbose_name="ID Interno Reloj Control"
    )

    # Archivos con validación de seguridad (TA-1.2)
    fotografia = models.ImageField(
        upload_to='empleados/fotos/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])],
        null=True, blank=True, verbose_name="Fotografía (Opcional)"
    )
    curriculum = models.FileField(
        upload_to='empleados/curriculums/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        null=True, blank=True, verbose_name="Currículum Vitae PDF (Opcional)"
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    @property
    def nombre_completo(self) -> str:
        partes = [
            self.primer_nombre, self.segundo_nombre,
            self.apellido_paterno, self.apellido_materno,
        ]
        return " ".join(p for p in partes if p).strip()

    def save(self, *args, **kwargs):
        if not self.codigo_reloj_control:
            with transaction.atomic():
                ultimo = Empleado.objects.select_for_update().order_by('-id').first()
                siguiente_num = (ultimo.id + 1) if ultimo else 1
                self.codigo_reloj_control = f"RC-{siguiente_num:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.rut} - {self.nombre_completo}"


class CargaFamiliar(models.Model):
    PARENTESCO_CHOICES = [
        ('CONYUGE', 'Cónyuge'),
        ('CONVIVIENTE_CIVIL', 'Conviviente Civil'),
        ('HIJO', 'Hijo / Hija'),
        ('PADRE_MADRE', 'Padre / Madre'),
        ('MADRE_VIUDA', 'Madre Viuda'),
        ('NIETO_BISNIETO', 'Nieto / Bisnieto (Huérfano)'),
        ('MENOR_TUTORIA', 'Menor en Tutoría Legal'),
    ]

    empleado = models.ForeignKey(
        Empleado, on_delete=models.CASCADE,
        related_name='cargas_familiares'
    )
    rut_carga = models.CharField(
        max_length=12, validators=[validar_rut_chileno], verbose_name="RUT Carga"
    )
    primer_nombre = models.CharField(max_length=50, verbose_name="Primer Nombre")
    segundo_nombre = models.CharField(
        max_length=50, blank=True, default='',
        verbose_name="Segundo Nombre (Opcional)"
    )
    apellido_paterno = models.CharField(max_length=50, verbose_name="Apellido Paterno")
    apellido_materno = models.CharField(max_length=50, verbose_name="Apellido Materno")
    fecha_nacimiento = models.DateField(verbose_name="Fecha de Nacimiento")
    parentesco = models.CharField(
        max_length=30, choices=PARENTESCO_CHOICES, verbose_name="Parentesco Legal"
    )

    @property
    def nombre_completo(self) -> str:
        partes = [
            self.primer_nombre, self.segundo_nombre,
            self.apellido_paterno, self.apellido_materno,
        ]
        return " ".join(p for p in partes if p).strip()

    def __str__(self):
        return f"{self.nombre_completo} ({self.get_parentesco_display()} de {self.empleado.rut})"


class RegistroAuditoria(models.Model):
    ACCION_CHOICES = [
        ('CREAR', 'Creación'),
        ('MODIFICAR', 'Modificación'),
        ('EDITAR', 'Actualización'),
        ('ELIMINAR', 'Eliminación'),
    ]

    usuario = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, verbose_name="Usuario Responsable"
    )
    accion = models.CharField(max_length=15, choices=ACCION_CHOICES, verbose_name="Acción")
    entidad = models.CharField(max_length=50, verbose_name="Módulo / Entidad")
    detalle = models.CharField(max_length=255, verbose_name="Detalle del Evento")
    ip_origen = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP de Origen")
    fecha_hora = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora")

    class Meta:
        ordering = ['-fecha_hora']
        verbose_name = "Registro de Auditoría"
        verbose_name_plural = "Registros de Auditoría"

    def __str__(self):
        user_str = self.usuario.username if self.usuario else "Sistema"
        fh = timezone.localtime(self.fecha_hora)
        return f"[{fh:%d/%m/%Y %H:%M}] {user_str} - {self.accion} en {self.entidad}"


class DocumentoEmitido(models.Model):
    """Trazabilidad de documentos generados (contratos y finiquitos)."""
    TIPO_CHOICES = [
        ('CONTRATO', 'Contrato de Trabajo'),
        ('FINIQUITO', 'Finiquito'),
    ]

    empleado = models.ForeignKey(
        Empleado, on_delete=models.CASCADE,
        related_name='documentos_emitidos', verbose_name="Empleado"
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="Tipo de Documento")
    parametros = models.JSONField(default=dict, verbose_name="Parámetros del Documento")
    emitido_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Emitido por (Usuario)"
    )
    fecha_emision = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora de Emisión")
    actualizado_en = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name="Última Actualización")

    class Meta:
        ordering = ['-fecha_emision']
        verbose_name = "Documento Emitido"
        verbose_name_plural = "Documentos Emitidos"

    def __str__(self):
        fh = timezone.localtime(self.fecha_emision)
        return f"{self.get_tipo_display()} - {self.empleado.rut} ({fh:%d/%m/%Y %H:%M})"
