from django.contrib import admin
from .models import (
    Empleado, CargaFamiliar, RegistroAuditoria, DocumentoEmitido,
    Concepto, LiquidacionSueldo,
)

admin.site.register(Empleado)
admin.site.register(CargaFamiliar)
admin.site.register(RegistroAuditoria)
admin.site.register(DocumentoEmitido)
admin.site.register(Concepto)
admin.site.register(LiquidacionSueldo)
