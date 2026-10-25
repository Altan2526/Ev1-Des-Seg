from django.db import models, transaction
from django.utils import timezone
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.contrib.auth.models import User
from .validators import validar_rut_chileno

import ast
import operator

# ---------------------------------------------------------------------------
# Safe arithmetic parser (AST-based — NEVER uses eval())
# DevSecOps / SonarQube: evita inyección de código en fórmulas paramétricas.
# ---------------------------------------------------------------------------

_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.FloorDiv: operator.floordiv,
}

_ALLOWED_UNARYOPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def safe_eval_arithmetic(expression: str, variables: dict) -> float:
    """
    Evalúa de forma segura una expresión aritmética usando el parser ``ast``.

    NUNCA utiliza ``eval()``. Únicamente permite:
    - Constantes numéricas (int, float)
    - Variables proporcionadas en ``variables``
    - Operadores binarios básicos (+, -, *, /, %, **, //)
    - Operadores unarios (+, -)

    Cualquier otro nodo (llamadas, atributos, subscript, etc.) lanza
    ``ValueError``.
    """
    if not expression or not isinstance(expression, str):
        raise ValueError("Fórmula vacía o no válida.")
    try:
        tree = ast.parse(expression.strip(), mode='eval')
    except SyntaxError:
        raise ValueError(f"Fórmula con sintaxis inválida: {expression}")
    return _eval_node(tree.body, variables)


def _eval_node(node, variables: dict):
    """Recursivamente evalúa un nodo AST restringido a aritmética básica."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Constante no numérica: {node.value!r}")
    if isinstance(node, ast.Name):
        if node.id in variables:
            return variables[node.id]
        raise ValueError(f"Variable no permitida en fórmula: {node.id}")
    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left, variables)
        right = _eval_node(node.right, variables)
        op_func = _ALLOWED_BINOPS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"Operador binario no permitido: {type(node.op).__name__}")
        return op_func(left, right)
    if isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand, variables)
        op_func = _ALLOWED_UNARYOPS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"Operador unario no permitido: {type(node.op).__name__}")
        return op_func(operand)
    raise ValueError(f"Nodo no permitido en fórmula: {type(node).__name__}")


# ---------------------------------------------------------------------------
# Modelos existentes (EV1DS-10) — sin cambios
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# EV1DS-06: Motor de Cálculo Paramétrico de Sueldos
# Modelos para conceptos salariales (haberes/descuentos/fórmulas) y
# liquidaciones de sueldo. Integra con EV1DS-10 obteniendo sueldo_base
# desde DocumentoEmitido.tipo='CONTRATO'.
# ---------------------------------------------------------------------------

class Concepto(models.Model):
    """
    Concepto paramétrico configurable: Haber o Descuento.

    - Habores: aumentan el sueldo (imponibles o no imponibles).
    - Descuentos: reducen el sueldo (legales como AFP/Salud o adicionales).

    El cálculo se realiza mediante ``safe_eval_arithmetic()`` evaluando la
    fórmula contra un contexto que incluye al menos ``sueldo_base``.
    """
    TIPO_CHOICES = [
        ('HABER', 'Haber'),
        ('DESCUENTO', 'Descuento'),
    ]
    CLASIFICACION_CHOICES = [
        ('IMPONIBLE', 'Imponible'),
        ('NO_IMPONIBLE', 'No Imponible'),
    ]

    codigo = models.CharField(
        max_length=20, unique=True, verbose_name="Código"
    )
    nombre = models.CharField(max_length=100, verbose_name="Nombre del Concepto")
    tipo = models.CharField(
        max_length=10, choices=TIPO_CHOICES, verbose_name="Tipo"
    )
    clasificacion = models.CharField(
        max_length=15, choices=CLASIFICACION_CHOICES,
        default='IMPONIBLE', verbose_name="Clasificación"
    )
    formula = models.CharField(
        max_length=200, blank=True, default='',
        help_text="Fórmula paramétrica (ej: 'sueldo_base * 0.10'). "
                  "Si está vacía, se usa monto_fijo.",
        verbose_name="Fórmula"
    )
    monto_fijo = models.IntegerField(
        default=0, validators=[MinValueValidator(0)],
        verbose_name="Monto Fijo (CLP)"
    )
    activo = models.BooleanField(
        default=True, verbose_name="Activo"
    )
    es_legal = models.BooleanField(
        default=True,
        help_text="Marcar para descuentos legales (AFP, Salud). "
                  "Desmarcar para descuentos adicionales.",
        verbose_name="Descuento Legal"
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['tipo', 'nombre']
        verbose_name = "Concepto Salarial"
        verbose_name_plural = "Conceptos Salariales"

    def __str__(self):
        return f"{self.codigo} - {self.nombre} ({self.get_tipo_display()})"

    def calcular(self, contexto: dict) -> int:
        """
        Calcula el valor del concepto.
        - Si tiene fórmula: la evalúa de forma segura con ``safe_eval_arithmetic``.
        - Si no tiene fórmula: devuelve ``monto_fijo``.
        El resultado se redondea a entero (CLP).
        """
        if self.formula:
            resultado = safe_eval_arithmetic(self.formula, contexto)
            return int(round(resultado))
        return self.monto_fijo


class LiquidacionSueldo(models.Model):
    """
    Liquidación de sueldo para un trabajador.

    Obtiene ``sueldo_base`` del contrato vigente emitido en EV1DS-10
    (``DocumentoEmitido`` con tipo='CONTRATO'). Si el trabajador no tiene
    contrato, la liquidación no puede generarse.
    """
    empleado = models.ForeignKey(
        Empleado, on_delete=models.CASCADE,
        related_name='liquidaciones', verbose_name="Empleado"
    )
    contrato_origen = models.ForeignKey(
        DocumentoEmitido, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='liquidaciones', verbose_name="Contrato de Origen (EV1DS-10)"
    )
    sueldo_base = models.IntegerField(verbose_name="Sueldo Base (CLP)")
    total_haberes = models.IntegerField(verbose_name="Total Haberes")
    total_descuentos = models.IntegerField(verbose_name="Total Descuentos")
    sueldo_liquido = models.IntegerField(verbose_name="Sueldo Líquido")
    detalle_conceptos = models.JSONField(
        default=dict, verbose_name="Detalle de Conceptos Aplicados"
    )
    periodo = models.CharField(
        max_length=10, verbose_name="Período (ej: 10/2024)"
    )
    fecha_emision = models.DateTimeField(
        default=timezone.now, verbose_name="Fecha de Emisión"
    )
    emitido_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Emitido por"
    )

    class Meta:
        ordering = ['-fecha_emision']
        verbose_name = "Liquidación de Sueldo"
        verbose_name_plural = "Liquidaciones de Sueldo"

    def __str__(self):
        fh = timezone.localtime(self.fecha_emision)
        return f"Liq. {self.empleado.nombre_completo} - {self.periodo} ({fh:%d/%m/%Y %H:%M})"
