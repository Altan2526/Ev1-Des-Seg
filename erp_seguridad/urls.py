from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', RedirectView.as_view(url='/rrhh/', permanent=False)),
    
    # Login principal
    path('login/', auth_views.LoginView.as_view(
        template_name='recursos_humanos/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    
    # NUEVA LÍNEA: Soluciona el error 404 buscando rrhh/login/
    path('rrhh/login/', auth_views.LoginView.as_view(
        template_name='recursos_humanos/login.html',
        redirect_authenticated_user=True
    ), name='rrhh_login'),

    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('admin/', admin.site.urls),
    path('rrhh/', include('recursos_humanos.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)