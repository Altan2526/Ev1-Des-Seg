from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_empleados, name='lista_empleados'),
    path('nuevo/', views.crear_empleado, name='crear_empleado'),
    path('<int:pk>/', views.detalle_empleado, name='detalle_empleado'),
    path('<int:pk>/editar/', views.editar_empleado, name='editar_empleado'),
    path('<int:pk>/eliminar/', views.eliminar_empleado, name='eliminar_empleado'),
    path('<int:empleado_pk>/cargas/<int:carga_pk>/eliminar/', views.eliminar_carga_familiar, name='eliminar_carga_familiar'),
    path('auditoria/', views.bitacora_auditoria, name='bitacora_auditoria'),
    path('licencias/', views.listar_licencias, name='listar_licencias'),
    path('licencias/nueva/', views.registrar_licencia, name='registrar_licencia'),
    path('licencias/registrar/', views.registrar_licencia, name='registrar_licencias'),
]
