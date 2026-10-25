from django.contrib import admin
from .models import Empleado, CargaFamiliar, RegistroAuditoria, DocumentoEmitido

admin.site.register(Empleado)
admin.site.register(CargaFamiliar)
admin.site.register(RegistroAuditoria)
admin.site.register(DocumentoEmitido)
