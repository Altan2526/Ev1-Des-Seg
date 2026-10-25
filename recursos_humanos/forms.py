from django import forms
from django.core.exceptions import ValidationError
from .models import Empleado, CargaFamiliar, Concepto
from .validators import (
    limpiar_y_formatear_rut,
    validar_rut_chileno,
    limpiar_y_formatear_telefono,
    validar_telefono_chileno,
)
from .models import safe_eval_arithmetic


class EmpleadoForm(forms.ModelForm):
    class Meta:
        model = Empleado
        fields = [
            'rut', 'primer_nombre', 'segundo_nombre',
            'apellido_paterno', 'apellido_materno', 'fecha_nacimiento',
            'direccion', 'telefono', 'email', 'cargo', 'centro_costo',
            'tipo_contrato', 'fecha_ingreso', 'prevision', 'afp',
            'fotografia', 'curriculum'
        ]
        widgets = {
            'rut': forms.TextInput(attrs={'placeholder': 'Ej: 18.456.789-2'}),
            'telefono': forms.TextInput(attrs={'placeholder': '+56 9 1111 1111'}),
            'email': forms.EmailInput(attrs={'placeholder': 'nombre@seguridadltda.cl'}),
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}),
            'fecha_ingreso': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        campos_opcionales = {'segundo_nombre', 'fotografia', 'curriculum'}
        for field_name, field in self.fields.items():
            field.required = field_name not in campos_opcionales
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'

    def clean_rut(self):
        rut = limpiar_y_formatear_rut(self.cleaned_data.get('rut', ''))
        validar_rut_chileno(rut)
        qs = Empleado.objects.filter(rut=rut)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Ya existe un empleado registrado con este RUT.")
        return rut

    def clean_telefono(self):
        telefono = limpiar_y_formatear_telefono(self.cleaned_data.get('telefono', ''))
        validar_telefono_chileno(telefono)
        return telefono

    def clean(self):
        cleaned_data = super().clean()
        campos_texto_obligatorios = [
            'primer_nombre', 'apellido_paterno', 'apellido_materno',
            'direccion', 'cargo'
        ]
        for campo in campos_texto_obligatorios:
            valor = cleaned_data.get(campo)
            if valor is not None and not str(valor).strip():
                self.add_error(campo, "Este campo es obligatorio y no puede contener solo espacios.")
            elif isinstance(valor, str):
                cleaned_data[campo] = valor.strip()
        return cleaned_data

    def clean_fotografia(self):
        foto = self.cleaned_data.get('fotografia')
        if foto and foto.size > 2 * 1024 * 1024:
            raise ValidationError("La fotografía no puede superar los 2MB.")
        return foto

    def clean_curriculum(self):
        cv = self.cleaned_data.get('curriculum')
        if cv and cv.size > 5 * 1024 * 1024:
            raise ValidationError("El currículum en PDF no puede superar los 5MB.")
        return cv


class CargaFamiliarForm(forms.ModelForm):
    class Meta:
        model = CargaFamiliar
        fields = [
            'rut_carga', 'primer_nombre', 'segundo_nombre',
            'apellido_paterno', 'apellido_materno',
            'fecha_nacimiento', 'parentesco'
        ]
        widgets = {
            'rut_carga': forms.TextInput(attrs={'placeholder': 'Ej: 24.111.222-3'}),
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.required = field_name != 'segundo_nombre'
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select form-select-sm'
            else:
                field.widget.attrs['class'] = 'form-control form-control-sm'

    def clean_rut_carga(self):
        rut = limpiar_y_formatear_rut(self.cleaned_data.get('rut_carga', ''))
        validar_rut_chileno(rut)
        return rut


# ---------------------------------------------------------------------------
# EV1DS-06: Formularios de Conceptos Salariales
# ---------------------------------------------------------------------------

class ConceptoForm(forms.ModelForm):
    """
    Formulario para crear / actualizar conceptos salariales (haberes y
    descuentos). Incluye validación estricta de la fórmula mediante
    ``safe_eval_arithmetic`` (nunca ``eval()``).
    """
    class Meta:
        model = Concepto
        fields = [
            'codigo', 'nombre', 'tipo', 'clasificacion',
            'formula', 'monto_fijo', 'activo', 'es_legal',
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Ej: GRAT, BONO, AFP, SALUD',
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Ej: Gratificación, Bono Producción, AFP',
            }),
            'tipo': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'clasificacion': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'formula': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': "Ej: sueldo_base * 0.10",
            }),
            'monto_fijo': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm', 'min': '0',
            }),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'es_legal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_formula(self):
        """
        Valida que la fórmula solo contenga operaciones aritméticas básicas
        y variables permitidas (sueldo_base). Nunca usa eval().
        """
        formula = self.cleaned_data.get('formula', '').strip()
        if not formula:
            return formula
        # Variables permitidas en fórmulas
        allowed_vars = {'sueldo_base', 'total_haberes', 'total_descuentos'}
        try:
            safe_eval_arithmetic(formula, {v: 1 for v in allowed_vars})
        except ValueError as e:
            raise ValidationError(
                f"Fórmula inválida o no permitida: {e}. "
                "Use solo números, operadores (+, -, *, /, %, **, //), "
                "paréntesis y la variable 'sueldo_base'."
            )
        return formula

    def clean_monto_fijo(self):
        monto = self.cleaned_data.get('monto_fijo', 0)
        if monto < 0:
            raise ValidationError("El monto fijo no puede ser negativo.")
        return monto