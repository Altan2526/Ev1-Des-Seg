from django.contrib import admin

from .models import (
    CargaFamiliar,
    Concepto,
    DocumentoEmitido,
    Empleado,
    LiquidacionSueldo,
    RegistroAuditoria,
)

admin.site.register(Empleado)
admin.site.register(CargaFamiliar)
admin.site.register(RegistroAuditoria)
admin.site.register(DocumentoEmitido)
admin.site.register(Concepto)
admin.site.register(LiquidacionSueldo)
