# 🦙 E-BOT PRO

> **"Llama que llama... por wasap"**  
> Sistema de gestión de turnos para clínicas con múltiples profesionales.

E-BOT PRO es la evolución de E-BOT LITE. Mientras LITE cubre un profesional y un consultorio, PRO está diseñado para clínicas con múltiples profesionales, agendas independientes, panel web centralizado y datos completos de pacientes.

---

## Índice

- [Características](#características)
- [Arquitectura](#arquitectura)
- [Stack tecnológico](#stack-tecnológico)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Base de datos](#base-de-datos)
- [Canales de acceso](#canales-de-acceso)
- [Flujos conversacionales](#flujos-conversacionales)
- [Panel web](#panel-web)
- [Variables de entorno](#variables-de-entorno)
- [Deploy en Railway](#deploy-en-railway)
- [Configuración inicial](#configuración-inicial)
- [Desarrollo local](#desarrollo-local)

---

## Características

- **Múltiples profesionales** con agendas independientes
- **Múltiples admins** — un admin por profesional + admin general
- **Paciente elige** especialidad y profesional al sacar turno
- **Identificación inteligente** — por teléfono con fallback por DNI
- **Datos completos del paciente** — nombre, DNI, obra social, plan
- **Mensajes con estado** — pendiente / leído (no se borran)
- **Reportes por profesional** y consolidados de la clínica
- **Panel web centralizado** para el admin general
- **Notificaciones automáticas** al paciente y al profesional
- **3 backends de storage** — PostgreSQL / memoria / archivo

---

## Arquitectura

```
                    ┌─────────────┐
                    │  PostgreSQL │
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │  Flask API  │
                    └──┬──────┬───┘
                       │      │
          ┌────────────┘      └────────────┐
   Twilio Webhook                    REST /admin/*
          │                                │
   ┌──────┴──────┐                 ┌───────┴──────┐
   │  WhatsApp   │                 │  Panel Web   │
   │  Paciente   │                 │  Admin Gral  │
   │  Profesional│                 └──────────────┘
   └─────────────┘
```

---

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| Backend | Python 3.11 + Flask 3.x |
| Base de datos | PostgreSQL (Railway) |
| Mensajería | Twilio WhatsApp API |
| Deploy | Railway |
| Panel web | Flask + Jinja2 (sin framework JS) |
| Storage conversacional | KV store sobre PostgreSQL |

---

## Estructura del proyecto

```
E-BOT-PRO/
├── app.py                  # Servidor Flask + registro de blueprints
├── config.py               # Variables de entorno y constantes
├── db.py                   # Schema SQL + funciones por entidad
├── storage.py              # KV store para conversation_state
├── services.py             # Lógica de negocio multi-profesional
├── handlers.py             # Router principal WhatsApp
├── handlers_paciente.py    # Flujo conversacional del paciente
├── handlers_admin.py       # Panel admin por WhatsApp
├── notifications.py        # Envío proactivo de mensajes Twilio
├── .env.example            # Plantilla de variables de entorno
├── requirements.txt        # Dependencias Python
├── railway.toml            # Configuración de deploy
├── templates/              # HTML del panel web
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── agenda.html
│   ├── mensajes.html
│   └── reportes.html
└── web/
    ├── __init__.py
    └── routes.py           # Blueprint Flask /admin/*
```

---

## Base de datos

El proyecto usa **tablas SQL relacionales** en PostgreSQL. El KV store queda exclusivamente para el estado de conversación WhatsApp.

### Tablas principales

| Tabla | Descripción |
|---|---|
| `professionals` | Profesionales de la clínica |
| `admins` | Admins por profesional + admin general |
| `patients` | Pacientes con DNI y obra social |
| `appointments` | Turnos activos y cancelados |
| `schedule_config` | Horarios por profesional y día de semana |
| `blocked_slots` | Bloqueos de agenda |
| `messages` | Mensajes entrantes con estado pending/read |
| `notifications` | Log de notificaciones enviadas |
| `kv_store` | Estado de conversación WhatsApp |

Las tablas se crean automáticamente al iniciar la aplicación con `init_db()`.

---

## Canales de acceso

### Paciente → WhatsApp
- Sacar turno (elige especialidad y profesional)
- Ver mis turnos próximos
- Cancelar turno
- Enviar mensaje al consultorio
- Urgencias

### Profesional → WhatsApp
- Ver turnos del día (con obra social del paciente)
- Ver próximos turnos
- Mensajes pendientes
- Nuevo turno manual
- Cancelar turno
- Bloquear su propia agenda
- Reporte del mes

### Admin general → Panel web `/admin`
- Dashboard con estadísticas globales
- Agenda de todos los profesionales
- Mensajes pendientes (todos o por profesional)
- Reportes mensuales consolidados o por profesional
- Nuevo turno, cancelar turno, bloquear agenda

---

## Flujos conversacionales

### Identificación del paciente

```
Mensaje entrante
      │
      ▼
¿Tiene perfil por teléfono?
      │
   Sí ──► Mostramos perfil ──► ¿Sos vos? S/N
      │                               │
      │                          N ──► Pedir DNI ──► Buscar por DNI
      │                                                    │
   No ──────────────────────────────────────────► ¿Existe?
                                                       │
                                                  Sí ──► Vincular teléfono
                                                  No ──► Registrar paciente nuevo
```

### Sacar turno (paciente)

```
1 Sacar turno
      │
      ▼
Identificación (teléfono / DNI)
      │
      ▼
Elegir profesional de la lista
      │
      ▼
Ingresar fecha (dd/mm/yyyy)
      │
      ▼
Elegir horario disponible
      │
      ▼
Confirmar turno S/N
      │
      ▼
✅ Turno confirmado → Notificación al paciente y al profesional
```

### Estados de conversación

| Estado | Descripción |
|---|---|
| `MENU` | Menú principal paciente |
| `CONFIRMAR_PERFIL` | Confirmación S/N del perfil encontrado |
| `PERFIL_DNI` | Ingreso de DNI para búsqueda |
| `PERFIL_NOMBRE` | Nombre y apellido (paciente nuevo) |
| `PERFIL_DNI_NUEVO` | DNI (paciente nuevo) |
| `PERFIL_OBRA_SOCIAL` | Obra social (paciente nuevo) |
| `ELEGIR_PROFESIONAL` | Selección de profesional |
| `TURNO_FECHA` | Ingreso de fecha |
| `TURNO_HORA` | Selección de horario |
| `CONFIRMAR_TURNO` | Confirmación final S/N |
| `MIS_TURNOS_CANCELAR` | Selección de turno a cancelar |
| `MENSAJE` | Redacción de mensaje libre |
| `ADMIN` | Menú admin WhatsApp |

---

## Panel web

Accesible en `/admin`. Login con contraseña definida en `web/routes.py`.

| Ruta | Vista |
|---|---|
| `/admin/` | Login |
| `/admin/dashboard` | Estadísticas + turnos del día por profesional |
| `/admin/agenda` | Agenda filtrable por profesional y fecha |
| `/admin/mensajes` | Mensajes pendientes |
| `/admin/reportes` | Reportes mensuales |
| `/admin/api/horarios` | API JSON — horarios libres |

---

## Variables de entorno

Copiar `.env.example` a `.env` y completar:

```env
# Base de datos (Railway la setea automáticamente)
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# Identidad
NOMBRE_CLINICA=Clínica San Martín

# Panel web
SECRET_KEY=clave-secreta-segura

# Modo desarrollo
MODO_TEST=false

# Storage
STORAGE_BACKEND=postgres
```

---

## Deploy en Railway

### Primera vez

1. Crear proyecto nuevo en [Railway](https://railway.app)
2. Conectar el repo `ebotsoluciones/E-BOT-PRO`
3. Agregar plugin **PostgreSQL** al proyecto
4. En **Variables** setear todas las del `.env.example`
5. Railway hace el deploy automáticamente

### Webhook Twilio

Una vez deployado, copiar la URL pública de Railway y configurar en Twilio:

```
https://tu-app.railway.app/webhook
```

Twilio → WhatsApp Sandbox (o número comprado) → Webhook URL → POST

### Comandos de Railway

```bash
# Ver logs en tiempo real
railway logs

# Variables de entorno
railway variables

# Redeploy manual
railway up
```

---

## Configuración inicial

Después del primer deploy, cargar los datos base desde Railway o una conexión directa a PostgreSQL:

```sql
-- 1. Crear profesional
INSERT INTO professionals (name, specialty, phone)
VALUES ('Dr. García', 'Clínica General', 'whatsapp:+5491100000000');

-- 2. Crear admin del profesional
INSERT INTO admins (phone, name, role, professional_id)
VALUES ('whatsapp:+5491100000000', 'Dr. García', 'professional', 1);

-- 3. Crear admin general
INSERT INTO admins (phone, name, role)
VALUES ('whatsapp:+5491199999999', 'Admin Clínica', 'general');

-- 4. Configurar agenda (lunes a viernes 9-18hs, slots de 30 min)
INSERT INTO schedule_config (professional_id, day_of_week, start_time, end_time, slot_minutes)
VALUES
  (1, 0, '09:00', '18:00', 30),  -- lunes
  (1, 1, '09:00', '18:00', 30),  -- martes
  (1, 2, '09:00', '18:00', 30),  -- miércoles
  (1, 3, '09:00', '18:00', 30),  -- jueves
  (1, 4, '09:00', '18:00', 30);  -- viernes
```

---

## Desarrollo local

```bash
# Clonar repo
git clone https://github.com/ebotsoluciones/E-BOT-PRO
cd E-BOT-PRO

# Instalar dependencias
pip install -r requirements.txt

# Copiar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# Modo sin DB (para pruebas rápidas)
STORAGE_BACKEND=memory MODO_TEST=true python app.py

# Con DB local
DATABASE_URL=postgresql://localhost/ebotpro python app.py

# Exponer al webhook de Twilio (requiere ngrok)
ngrok http 5000
# Copiar la URL https de ngrok a Twilio como webhook
```

---

## Diferencias respecto a E-BOT LITE

| | LITE | PRO |
|---|---|---|
| Profesionales | 1 fijo | Múltiples desde DB |
| Admins | Lista fija en config | Tabla en DB con roles |
| Pacientes | Solo nombre y teléfono | DNI + obra social + plan |
| Horarios | Variables de entorno | Por profesional y día en DB |
| Mensajes | Se borran | Estado pending/read |
| Reportes | Solo del mes | Por profesional + consolidado |
| Panel web | No | Sí — Flask + Jinja2 |
| Identificación | Solo por teléfono | Teléfono + fallback por DNI |

---

## Roadmap

- [ ] Recordatorios automáticos 24hs antes del turno
- [ ] Interactive Messages de WhatsApp (List Messages / Quick Reply)
- [ ] Buscador de pacientes en el panel web
- [ ] Exportar reportes a Excel
- [ ] Login del panel web con tabla de admins (en lugar de contraseña fija)
- [ ] Gestión de profesionales desde el panel web

---
---

## Migraciones SQL

Esta sección documenta los cambios de schema que requieren SQL manual cuando se migra una base de datos existente (no aplica a instalaciones nuevas).

### v1.0 → v1.1 — Separación de nombre en professionals

En la versión inicial la tabla `professionals` tenía una sola columna `name`. En v1.1 se separó en `last_name` y `first_name`.

**Solo ejecutar si la DB ya existe con la estructura vieja:**

```sql
-- 1. Agregar columnas nuevas
ALTER TABLE professionals 
ADD COLUMN last_name  VARCHAR(100),
ADD COLUMN first_name VARCHAR(100);

-- 2. Migrar datos existentes
UPDATE professionals SET last_name = name, first_name = '';

-- 3. Aplicar restricciones y liberar columna vieja
ALTER TABLE professionals 
ALTER COLUMN last_name  SET NOT NULL,
ALTER COLUMN first_name SET NOT NULL,
ALTER COLUMN name DROP NOT NULL;
```

**Instalaciones nuevas** — no requieren este paso.
MODO_TEST=true en las variables de Railway — eso bypasea la validación de admins y cualquiera puede escribir adm para entrar.
Ahora seguramente lo cambiaste a false o lo sacaste. Dos opciones:
Opción A — Insertar tu número en la tabla admins (correcto para producción)
sqlINSERT INTO admins (phone, name, role)
VALUES ('whatsapp:+5493515645624', 'Eduard', 'general');
Opción B — Dejar MODO_TEST=true por ahora mientras seguís desarrollando, y escribís adm para entrar al panel admin.
*E-BOT PRO — ebotsoluciones 🦙*
