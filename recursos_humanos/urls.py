from django.urls import path
from . import views

urlpatterns = [
    # Rutas de gestión de personal
    path('', views.lista_empleados, name='lista_empleados'),
    path('nuevo/', views.crear_empleado, name='crear_empleado'),
    path('<int:pk>/', views.detalle_empleado, name='detalle_empleado'),
    path('<int:pk>/editar/', views.editar_empleado, name='editar_empleado'),
    path('<int:pk>/eliminar/', views.eliminar_empleado, name='eliminar_empleado'),
    path('<int:empleado_pk>/cargas/<int:carga_pk>/eliminar/', views.eliminar_carga_familiar, name='eliminar_carga_familiar'),
    path('auditoria/', views.bitacora_auditoria, name='bitacora_auditoria'),

    # Rutas de emisión de documentos (EV1DS-10)
    path('documentos/', views.gestion_documentos, name='gestion_documentos'),
    path('documentos/<str:tipo>/<int:empleado_id>/', views.descargar_documento_individual, name='descargar_documento_individual'),
    path('documentos/masivo/', views.descargar_documentos_masivos, name='descargar_documentos_masivos'),

    # Rutas de cálculo paramétrico de sueldos (EV1DS-06)
    path('sueldos/', views.calculo_sueldos, name='calculo_sueldos'),
    path('sueldos/concepto/', views.configurar_concepto, name='configurar_concepto'),
    path('sueldos/generar/<int:empleado_id>/', views.generar_liquidacion, name='generar_liquidacion'),
    path('sueldos/preview/<int:liquidacion_id>/', views.previsualizar_liquidacion, name='previsualizar_liquidacion'),
    path('sueldos/descargar/<int:liquidacion_id>/', views.descargar_liquidacion_pdf, name='descargar_liquidacion_pdf'),
    path('documentos/preview/<str:tipo>/<int:empleado_id>/', views.previsualizar_documento, name='previsualizar_documento'),
]
