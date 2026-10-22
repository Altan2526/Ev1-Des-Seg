from django.urls import path
from . import views

urlpatterns = [
    # Rutas existentes de gestión de personal
    path('', views.lista_empleados, name='lista_empleados'),
    path('nuevo/', views.crear_empleado, name='crear_empleado'),
    path('<int:pk>/', views.detalle_empleado, name='detalle_empleado'),
    path('<int:pk>/editar/', views.editar_empleado, name='editar_empleado'),
    path('<int:pk>/eliminar/', views.eliminar_empleado, name='eliminar_empleado'),
    path('<int:empleado_pk>/cargas/<int:carga_pk>/eliminar/', views.eliminar_carga_familiar, name='eliminar_carga_familiar'),
    path('auditoria/', views.bitacora_auditoria, name='bitacora_auditoria'),

    # Rutas de emisión de documentos (utilizadas por las ventanitas modales)
    path('documentos/<str:tipo>/<int:empleado_id>/', views.descargar_documento_individual, name='descargar_documento_individual'),
    path('documentos/masivo/', views.descargar_documentos_masivos, name='descargar_documentos_masivos'),
    path('documentos/', views.panel_documentos, name='panel_documentos'),
]