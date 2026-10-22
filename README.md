# Ev1-Des-Seg

# ERP "Seguridad LTDA" - Módulo de Recursos Humanos

Sistema web desarrollado en **Django** bajo metodología ágil **Scrum** y cultura **DevSecOps** (principio *Shift Left*), enfocado en la gestión segura de fichas del personal, cargas familiares, validaciones de integridad de datos y control de acceso.

---

## 1. Requisitos Previos

Antes de iniciar el proyecto, asegúrate de tener instalado en tu equipo:
* **Python 3.10** o superior.
* **Git** para el control de versiones.

---

## 2. Instalación y Configuración del Entorno

Sigue estos pasos en orden dentro de tu terminal para levantar el proyecto por primera vez:

### Paso 1: Clonar el repositorio
```bash
git clone <URL_DEL_REPOSITORIO>
cd <NOMBRE_DE_LA_CARPETA>
```

### Paso 2: Crear y activar el entorno virtual (`venv`)
* **En Linux / macOS:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```
* **En Windows (CMD o PowerShell):**
  ```powershell
  python -m venv venv
  venv\Scripts\activate
  ```

### Paso 3: Instalar las dependencias del proyecto
Con el entorno virtual activado, instala los paquetes requeridos (`Django`, `Pillow`, `python-dotenv`, etc.):
```bash
pip install -r requirements.txt
```

### Paso 4: Configurar las variables de entorno (`.env`)
Por políticas de seguridad DevSecOps, las claves secretas no se suben al repositorio. En la raíz del proyecto encontrarás el archivo de plantilla **`.env_example`**.

1. Crea una copia de ese archivo y llámala exactamente **`.env`** (en la misma carpeta donde está `manage.py`):
   * **Linux / macOS:**
     ```bash
     cp .env_example .env
     ```
   * **Windows:**
     ```powershell
     copy .env_example .env
     ```
2. Verifica que dentro de tu archivo `.env` estén definidas las variables:
   ```env
   DJANGO_SECRET_KEY=clave-super-secreta-desarrollo-erp-seguridad-2026
   DJANGO_DEBUG=True
   ```

---

## 3. Base de Datos y Creación del Primer Usuario

Como el archivo de base de datos local (`db.sqlite3`) está excluido en el `.gitignore` por seguridad, **cada integrante debe inicializar su propia base de datos local** al descargar el proyecto.

> **Nota:** El proyecto incluye un **fixture de datos de ejemplo** (`datos_iniciales`) que ya contiene un usuario administrador listo para usar. Si cargas el fixture (ver [Sección 4](#4-carga-de-datos-de-ejemplo-fixture)](#4-carga-de-datos-de-ejemplo-fixture)) puedes **omitir** la creación manual del usuario.

### Paso 1: Ejecutar las migraciones
Genera y aplica las tablas del modelo de datos (`Empleado`, `CargaFamiliar` y tablas de sesión de Django) ejecutando:
```bash
python manage.py makemigrations
python manage.py migrate
```

### Paso 2: Crear el primer usuario (Administrador de RRHH)
Dado que todas las rutas del módulo están protegidas contra accesos no autorizados (`@login_required`), necesitas crear una cuenta para poder iniciar sesión en la plataforma:

```bash
python manage.py createsuperuser
```

La terminal te solicitará los siguientes datos de forma interactiva:
1. **Username:** Ingresa un nombre de usuario (ej. `admin_rrhh`).
2. **Email address:** Ingresa un correo (ej. `rrhh@seguridadltda.cl`) o presiona *Enter* para omitir.
3. **Password / Password (again):** Escribe tu contraseña (ej. `Seguridad2026!`).
   * *Nota:* Por seguridad, mientras escribes la contraseña en la terminal no se mostrarán caracteres ni asteriscos en pantalla; simplemente escríbela y presiona *Enter*.

---

## 4. Carga de Datos de Ejemplo (Fixture)

El proyecto incluye un **archivo de datos ficticios** (`datos_iniciales.json`) que contiene:

* **1 usuario administrador** (`admin_rrhh` / `AdminRrhh2026!`) con permisos de superuser.
* **7 empleados** con RUTs chilenos válidos (verificados con Módulo 11), distribuidos en todos los centros de costo y tipos de contrato.
* **7 cargas familiares** relacionadas a los empleados.
* **6 registros de auditoría** simulando actividad previa.

### Cómo cargar los datos

Después de ejecutar las migraciones (y **opcionalmente** después de crear tu usuario administrador), puedes cargar los datos de ejemplo de una sola vez:

```bash
python manage.py loaddata datos_iniciales
```

Django localizará automáticamente el archivo en `recursos_humanos/fixtures/datos_iniciales.json` y cargará **21 registros** (1 usuario + 7 empleados + 7 cargas + 6 auditorías).

### Credenciales de acceso con los datos de ejemplo

| Campo       | Valor                       |
|-------------|-----------------------------|
| **Usuario** | `admin_rrhh`                |
| **Contraseña** | `AdminRrhh2026!`          |

Con estos datos ya no necesitas ejecutar `python manage.py createsuperuser` cada vez que configures el entorno desde cero.

### Recargar los datos desde cero (opcional)

Si ya tienes datos en la base y quieres empezar limpio con el fixture:

```bash
python manage.py flush --no-input
python manage.py loaddata datos_iniciales
```

### Estructura del fixture

```
recursos_humanos/
├── fixtures/
│   └── datos_iniciales.json   # Archivo con datos ficticios
├── migrations/
├── models.py
└── ...
```

---

## 5. Arranque del Servidor y Pruebas de Funcionamiento

### 1. Iniciar el servidor de desarrollo
Ejecuta el siguiente comando para levantar la aplicación:
```bash
python manage.py runserver
```

### 2. Rutas principales del sistema
Con el servidor activo, abre tu navegador web e ingresa a:
* **Acceso principal / Módulo RRHH:** `http://127.0.0.1:8000/` (redirige automáticamente a `/login/` si no has iniciado sesión, o a `/rrhh/` si ya estás autenticado).
* **Panel de Administración Django (Back-Office):** `http://127.0.0.1:8000/admin/`

### 3. Lista de chequeo para probar que la página funciona (QA)
Una vez dentro de `http://127.0.0.1:8000/` con el usuario que creaste en el paso anterior, realiza las siguientes pruebas:

1. **Inicio y Cierre de Sesión:**
   * Inicia sesión en `/login/` y verifica que redirija directamente al listado de **Fichas del Personal** (`/rrhh/`) mostrando tu nombre de usuario en la barra superior.
   * Prueba el botón rojo **Cerrar Sesión** (protegido mediante petición `POST` y token CSRF) para confirmar que finaliza la sesión y retorna al login.
2. **Creación de Ficha de Empleado (`/rrhh/nuevo/`):**
   * Verifica que los campos obligatorios estén marcados con `*`.
   * **Prueba de RUT (Módulo 11):** Escribe un RUT inválido (ej. `21.564.898-7`) y comprueba que el sistema muestre el error inmediatamente al terminar de escribir. Luego ingresa un RUT válido (ej. `21.564.898-3` o `11.111.111-1`).
   * **Prueba de Teléfono Chileno:** Escribe un número móvil de 9 dígitos (ej. `912345678`) o fijo (`221234567`) y comprueba que se auto-formatee a `+56 9 1234 5678` o `+56 2 2123 4567`.
   * **Prueba de Archivos Seguros:** Sube una fotografía (`.jpg` / `.png` máx. 2MB) y un currículum (`.pdf` máx. 5MB). Intenta subir un archivo con otra extensión para comprobar el bloqueo de seguridad.
3. **Verificación de IDs Internos y Cargas Familiares:**
   * Al guardar el empleado, verifica en la tabla principal que el sistema haya generado automáticamente el **ID de Reloj Control** (`RC-0001`) y el código interno del **Centro de Costo** (`CC-XXX`).
   * Haz clic en **Ver Ficha** y registra una **Carga Familiar** en el panel derecho para comprobar la relación en la base de datos.
