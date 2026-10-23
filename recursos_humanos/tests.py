from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from datetime import date
from decimal import Decimal
from .models import Empleado, LicenciaMedica, RegistroAuditoria


class LicenciasTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='Password123!'
        )
        self.empleado = Empleado.objects.create(
            rut='11.111.111-1',
            primer_nombre='Juan',
            apellido_paterno='Pérez',
            apellido_materno='González',
            fecha_nacimiento=date(1990, 5, 15),
            direccion='Av. Providencia 1234',
            telefono='+56 9 1234 5678',
            email='juan.perez@seguridadltda.cl',
            cargo='Guardia de Seguridad',
            centro_costo='CC-300',
            tipo_contrato='INDEFINIDO',
            fecha_ingreso=date(2022, 1, 10),
            prevision='FONASA',
            afp='HABITAT',
        )

    def test_listar_licencias_requiere_login(self):
        response = self.client.get(reverse('listar_licencias'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_listar_licencias_vacia(self):
        self.client.login(username='testuser', password='Password123!')
        response = self.client.get(reverse('listar_licencias'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recursos_humanos/listar_licencias.html')
        self.assertContains(response, 'No hay licencias médicas registradas')

    def test_listar_licencias_con_datos(self):
        self.client.login(username='testuser', password='Password123!')
        LicenciaMedica.objects.create(
            empleado=self.empleado,
            fecha_inicio=date(2026, 10, 1),
            fecha_fin=date(2026, 10, 5),
            tipo_licencia='ENFERMEDAD',
            dias=5,
            monto=Decimal('150000.00'),
            motivo='Reposo médico por lumbago agudo',
            registrado_por=self.user
        )

        response = self.client.get(reverse('listar_licencias'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recursos_humanos/listar_licencias.html')
        self.assertContains(response, 'Juan Pérez González')
        self.assertContains(response, '11.111.111-1')
        self.assertContains(response, 'Enfermedad Común')
        self.assertContains(response, '150000.00')
        self.assertContains(response, 'testuser')

    def test_registrar_licencia_get(self):
        self.client.login(username='testuser', password='Password123!')
        response = self.client.get(reverse('registrar_licencia'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recursos_humanos/registrar_licencias.html')
        self.assertContains(response, 'Módulo de Recursos Humanos - Registro de Licencias Médicas')
        self.assertContains(response, 'Juan Pérez González')

    def test_registrar_licencia_post_valido(self):
        self.client.login(username='testuser', password='Password123!')
        datos = {
            'empleado': self.empleado.id,
            'fecha_inicio': '2026-11-01',
            'fecha_fin': '2026-11-10',
            'tipo_licencia': 'MATERNAL',
            'dias': 10,
            'monto': '250000.00',
            'motivo': 'Licencia prenatal regular',
        }
        response = self.client.post(reverse('registrar_licencia'), datos, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recursos_humanos/listar_licencias.html')
        self.assertTrue(LicenciaMedica.objects.filter(empleado=self.empleado, tipo_licencia='MATERNAL').exists())
        licencia = LicenciaMedica.objects.get(empleado=self.empleado, tipo_licencia='MATERNAL')
        self.assertEqual(licencia.registrado_por, self.user)
        self.assertTrue(RegistroAuditoria.objects.filter(entidad='Licencia Médica', accion='CREAR').exists())

    def test_registrar_licencia_fechas_invalidas(self):
        self.client.login(username='testuser', password='Password123!')
        datos = {
            'empleado': self.empleado.id,
            'fecha_inicio': '2026-11-10',
            'fecha_fin': '2026-11-01',  # Fecha de fin anterior a inicio
            'tipo_licencia': 'ENFERMEDAD',
            'dias': 5,
            'monto': '100000.00',
            'motivo': 'Prueba fecha inválida',
        }
        response = self.client.post(reverse('registrar_licencia'), datos)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recursos_humanos/registrar_licencias.html')
        form = response.context['form']
        self.assertTrue(form.errors)
        self.assertIn('fecha_fin', form.errors)
        self.assertIn('La fecha de término no puede ser anterior a la fecha de inicio.', form.errors['fecha_fin'])
        self.assertFalse(LicenciaMedica.objects.filter(motivo='Prueba fecha inválida').exists())
