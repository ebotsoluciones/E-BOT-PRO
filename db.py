
"""
db.py — capa de base de datos E-BOT PRO 🦙🔥
Gestiona conexión PostgreSQL y schema completo.
"""

import psycopg2
import psycopg2.extras
from config import DATABASE_URL


# ═══════════════════════════════════════════════════════════════════════════════
# CONEXIÓN
# ═══════════════════════════════════════════════════════════════════════════════

_conn = None

def get_conn():
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg2.connect(DATABASE_URL)
        _conn.autocommit = True
    return _conn

def get_cursor():
    return get_conn().cursor(cursor_factory=psycopg2.extras.RealDictCursor)


# ═══════════════════════════════════════════════════════════════════════════════
# INICIALIZACIÓN DE TABLAS
# ═══════════════════════════════════════════════════════════════════════════════

def init_db():
    """Crea todas las tablas si no existen. Seguro para correr en cada startup."""
    with get_cursor() as cur:

        cur.execute("""
            CREATE TABLE IF NOT EXISTS kv_store (
                key  TEXT PRIMARY KEY,
                val  TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS professionals (
                id               SERIAL PRIMARY KEY,
                last_name        VARCHAR(100) NOT NULL,
                first_name       VARCHAR(100) NOT NULL,
                specialty        VARCHAR(100),
                phone            VARCHAR(30),
                active           BOOLEAN DEFAULT TRUE,
                acepta_mensajes  BOOLEAN DEFAULT TRUE,
                created_at       TIMESTAMP DEFAULT NOW()
            )
        """)

        # Migración: agregar acepta_mensajes si no existe
        cur.execute("""
            ALTER TABLE professionals
            ADD COLUMN IF NOT EXISTS acepta_mensajes BOOLEAN DEFAULT TRUE
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id              SERIAL PRIMARY KEY,
                phone           VARCHAR(30) UNIQUE NOT NULL,
                name            VARCHAR(100),
                role            VARCHAR(20) DEFAULT 'professional',
                professional_id INTEGER REFERENCES professionals(id) ON DELETE SET NULL,
                active          BOOLEAN DEFAULT TRUE,
                created_at      TIMESTAMP DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id          SERIAL PRIMARY KEY,
                phone       VARCHAR(30),
                name        VARCHAR(100) NOT NULL,
                dni         VARCHAR(20) UNIQUE,
                obra_social VARCHAR(100),
                plan        VARCHAR(100),
                notes       TEXT,
                created_at  TIMESTAMP DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS schedule_config (
                id              SERIAL PRIMARY KEY,
                professional_id INTEGER NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
                day_of_week     SMALLINT NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
                start_time      TIME NOT NULL,
                end_time        TIME NOT NULL,
                slot_minutes    SMALLINT DEFAULT 30,
                UNIQUE (professional_id, day_of_week)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id              SERIAL PRIMARY KEY,
                professional_id INTEGER NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
                patient_id      INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
                date            DATE NOT NULL,
                time            TIME NOT NULL,
                status          VARCHAR(20) DEFAULT 'active',
                notes           TEXT,
                created_by      VARCHAR(20) DEFAULT 'patient',
                notified_at     TIMESTAMP,
                cancelled_by    VARCHAR(20),
                cancel_reason   TEXT,
                created_at      TIMESTAMP DEFAULT NOW(),
                UNIQUE (professional_id, date, time, status)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS blocked_slots (
                id              SERIAL PRIMARY KEY,
                professional_id INTEGER NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
                date            DATE NOT NULL,
                time_from       TIME NOT NULL,
                time_to         TIME NOT NULL,
                reason          TEXT,
                created_by      VARCHAR(30),
                created_at      TIMESTAMP DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id              SERIAL PRIMARY KEY,
                patient_id      INTEGER REFERENCES patients(id) ON DELETE SET NULL,
                professional_id INTEGER REFERENCES professionals(id) ON DELETE SET NULL,
                direction       VARCHAR(5) DEFAULT 'in',
                content         TEXT NOT NULL,
                status          VARCHAR(10) DEFAULT 'pending',
                read_at         TIMESTAMP,
                created_at      TIMESTAMP DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id              SERIAL PRIMARY KEY,
                appointment_id  INTEGER REFERENCES appointments(id) ON DELETE CASCADE,
                recipient_phone VARCHAR(30) NOT NULL,
                type            VARCHAR(20) NOT NULL,
                status          VARCHAR(10) DEFAULT 'pending',
                sent_at         TIMESTAMP,
                error_msg       TEXT,
                created_at      TIMESTAMP DEFAULT NOW()
            )
        """)

        print("[DB] Tablas inicializadas correctamente ✅")


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def prof_display_name(prof: dict) -> str:
    """Apellido, Nombre — Especialidad"""
    nombre = f"{prof['last_name']}, {prof['first_name']}"
    if prof.get('specialty'):
        nombre += f" — {prof['specialty']}"
    return nombre

def prof_short_name(prof: dict) -> str:
    """Apellido, Nombre"""
    return f"{prof['last_name']}, {prof['first_name']}"


# ═══════════════════════════════════════════════════════════════════════════════
# PROFESSIONALS
# ═══════════════════════════════════════════════════════════════════════════════

def get_professionals(active_only=True) -> list:
    with get_cursor() as cur:
        if active_only:
            cur.execute("""
                SELECT * FROM professionals
                WHERE active = TRUE ORDER BY last_name, first_name
            """)
        else:
            cur.execute("""
                SELECT * FROM professionals ORDER BY last_name, first_name
            """)
        return cur.fetchall()

def get_professional_by_id(prof_id: int) -> dict:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM professionals WHERE id = %s", (prof_id,))
        return cur.fetchone()

def get_professional_by_phone(phone: str) -> dict:
    with get_cursor() as cur:
        cur.execute("""
            SELECT p.* FROM professionals p
            JOIN admins a ON a.professional_id = p.id
            WHERE a.phone = %s AND a.active = TRUE
        """, (phone,))
        return cur.fetchone()

def create_professional(last_name: str, first_name: str,
                        specialty: str = None, phone: str = None) -> dict:
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO professionals (last_name, first_name, specialty, phone)
            VALUES (%s, %s, %s, %s) RETURNING *
        """, (last_name.strip().title(), first_name.strip().title(), specialty, phone))
        return cur.fetchone()

def update_professional(prof_id: int, last_name: str, first_name: str,
                        specialty: str = None, phone: str = None, active: bool = True):
    with get_cursor() as cur:
        cur.execute("""
            UPDATE professionals
            SET last_name = %s, first_name = %s,
                specialty = %s, phone = %s, active = %s
            WHERE id = %s
        """, (last_name.strip().title(), first_name.strip().title(),
              specialty, phone, active, prof_id))

def deactivate_professional(prof_id: int):
    """Baja lógica — no elimina, marca como inactivo."""
    with get_cursor() as cur:
        cur.execute("""
            UPDATE professionals SET active = FALSE WHERE id = %s
        """, (prof_id,))


# ═══════════════════════════════════════════════════════════════════════════════
# ADMINS
# ═══════════════════════════════════════════════════════════════════════════════

def get_admin_by_phone(phone: str) -> dict:
    with get_cursor() as cur:
        cur.execute("""
            SELECT * FROM admins WHERE phone = %s AND active = TRUE
        """, (phone,))
        return cur.fetchone()

def get_all_admins() -> list:
    with get_cursor() as cur:
        cur.execute("""
            SELECT a.*, p.last_name, p.first_name
            FROM admins a
            LEFT JOIN professionals p ON p.id = a.professional_id
            ORDER BY a.role, a.name
        """)
        return cur.fetchall()

def create_admin(phone: str, name: str, role: str = 'professional',
                 professional_id: int = None) -> dict:
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO admins (phone, name, role, professional_id)
            VALUES (%s, %s, %s, %s) RETURNING *
        """, (phone, name, role, professional_id))
        return cur.fetchone()

def is_admin(phone: str) -> bool:
    return get_admin_by_phone(phone) is not None

def is_general_admin(phone: str) -> bool:
    admin = get_admin_by_phone(phone)
    return admin is not None and admin["role"] == "general"


# ═══════════════════════════════════════════════════════════════════════════════
# PATIENTS
# ═══════════════════════════════════════════════════════════════════════════════

def get_patient_by_phone(phone: str) -> dict:
    with get_cursor() as cur:
        cur.execute("""
            SELECT * FROM patients
            WHERE phone = %s ORDER BY created_at DESC LIMIT 1
        """, (phone,))
        return cur.fetchone()

def get_patient_by_dni(dni: str) -> dict:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM patients WHERE dni = %s", (dni,))
        return cur.fetchone()

def get_patient_by_id(patient_id: int) -> dict:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM patients WHERE id = %s", (patient_id,))
        return cur.fetchone()

def get_all_patients() -> list:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM patients ORDER BY name")
        return cur.fetchall()

def create_patient(phone: str, name: str, dni: str,
                   obra_social: str = None, plan: str = None) -> dict:
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO patients (phone, name, dni, obra_social, plan)
            VALUES (%s, %s, %s, %s, %s) RETURNING *
        """, (phone, name, dni, obra_social, plan))
        return cur.fetchone()

def update_patient_phone(patient_id: int, phone: str):
    with get_cursor() as cur:
        cur.execute("""
            UPDATE patients SET phone = %s WHERE id = %s
        """, (phone, patient_id))


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEDULE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

def get_schedule(prof_id: int) -> list:
    with get_cursor() as cur:
        cur.execute("""
            SELECT * FROM schedule_config
            WHERE professional_id = %s ORDER BY day_of_week
        """, (prof_id,))
        return cur.fetchall()

def get_schedule_for_day(prof_id: int, day_of_week: int) -> dict:
    with get_cursor() as cur:
        cur.execute("""
            SELECT * FROM schedule_config
            WHERE professional_id = %s AND day_of_week = %s
        """, (prof_id, day_of_week))
        return cur.fetchone()

def upsert_schedule(prof_id: int, day_of_week: int, start_time: str,
                    end_time: str, slot_minutes: int = 30):
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO schedule_config
                (professional_id, day_of_week, start_time, end_time, slot_minutes)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (professional_id, day_of_week)
            DO UPDATE SET start_time   = EXCLUDED.start_time,
                          end_time     = EXCLUDED.end_time,
                          slot_minutes = EXCLUDED.slot_minutes
        """, (prof_id, day_of_week, start_time, end_time, slot_minutes))

def delete_schedule(prof_id: int):
    with get_cursor() as cur:
        cur.execute("""
            DELETE FROM schedule_config WHERE professional_id = %s
        """, (prof_id,))


# ═══════════════════════════════════════════════════════════════════════════════
# APPOINTMENTS
# ═══════════════════════════════════════════════════════════════════════════════

def get_appointments_by_date(prof_id: int, date: str) -> list:
    with get_cursor() as cur:
        cur.execute("""
            SELECT a.*, p.name as patient_name, p.phone as patient_phone,
                   p.dni, p.obra_social, p.plan
            FROM appointments a
            JOIN patients p ON p.id = a.patient_id
            WHERE a.professional_id = %s AND a.date = %s AND a.status = 'active'
            ORDER BY a.time
        """, (prof_id, date))
        return cur.fetchall()

def get_upcoming_appointments(prof_id: int) -> list:
    with get_cursor() as cur:
        cur.execute("""
            SELECT a.*, p.name as patient_name, p.phone as patient_phone
            FROM appointments a
            JOIN patients p ON p.id = a.patient_id
            WHERE a.professional_id = %s
              AND a.date >= CURRENT_DATE AND a.status = 'active'
            ORDER BY a.date, a.time
        """, (prof_id,))
        return cur.fetchall()

def get_patient_appointments(patient_id: int) -> list:
    with get_cursor() as cur:
        cur.execute("""
            SELECT a.*,
                   pr.last_name  as prof_last_name,
                   pr.first_name as prof_first_name,
                   pr.specialty
            FROM appointments a
            JOIN professionals pr ON pr.id = a.professional_id
            WHERE a.patient_id = %s
              AND a.date >= CURRENT_DATE AND a.status = 'active'
            ORDER BY a.date, a.time
        """, (patient_id,))
        return cur.fetchall()

def is_slot_taken(prof_id: int, date: str, time: str) -> bool:
    with get_cursor() as cur:
        cur.execute("""
            SELECT 1 FROM appointments
            WHERE professional_id = %s AND date = %s
              AND time = %s AND status = 'active'
        """, (prof_id, date, time))
        return cur.fetchone() is not None

def create_appointment(prof_id: int, patient_id: int, date: str, time: str,
                       created_by: str = "patient", notes: str = None) -> dict:
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO appointments
                (professional_id, patient_id, date, time, created_by, notes)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING *
        """, (prof_id, patient_id, date, time, created_by, notes))
        return cur.fetchone()

def cancel_appointment(appointment_id: int, cancelled_by: str = "patient",
                       reason: str = None):
    with get_cursor() as cur:
        cur.execute("""
            UPDATE appointments
            SET status = 'cancelled', cancelled_by = %s, cancel_reason = %s
            WHERE id = %s
        """, (cancelled_by, reason, appointment_id))

def get_appointment_by_slot(prof_id: int, date: str, time: str) -> dict:
    with get_cursor() as cur:
        cur.execute("""
            SELECT a.*, p.name as patient_name, p.phone as patient_phone
            FROM appointments a JOIN patients p ON p.id = a.patient_id
            WHERE a.professional_id = %s AND a.date = %s
              AND a.time = %s AND a.status = 'active'
        """, (prof_id, date, time))
        return cur.fetchone()


# ═══════════════════════════════════════════════════════════════════════════════
# BLOCKED SLOTS
# ═══════════════════════════════════════════════════════════════════════════════

def is_slot_blocked(prof_id: int, date: str, time: str) -> bool:
    with get_cursor() as cur:
        cur.execute("""
            SELECT 1 FROM blocked_slots
            WHERE professional_id = %s AND date = %s
              AND time_from <= %s AND time_to > %s
        """, (prof_id, date, time, time))
        return cur.fetchone() is not None

def block_slot(prof_id: int, date: str, time_from: str, time_to: str,
               reason: str = None, created_by: str = None):
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO blocked_slots
                (professional_id, date, time_from, time_to, reason, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (prof_id, date, time_from, time_to, reason, created_by))

def get_blocked_slots(prof_id: int, date: str) -> list:
    with get_cursor() as cur:
        cur.execute("""
            SELECT * FROM blocked_slots
            WHERE professional_id = %s AND date = %s ORDER BY time_from
        """, (prof_id, date))
        return cur.fetchall()


# ═══════════════════════════════════════════════════════════════════════════════
# MESSAGES
# ═══════════════════════════════════════════════════════════════════════════════

def save_message(patient_id: int, content: str, prof_id: int = None,
                 direction: str = "in") -> dict:
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO messages (patient_id, professional_id, direction, content)
            VALUES (%s, %s, %s, %s) RETURNING *
        """, (patient_id, prof_id, direction, content))
        return cur.fetchone()

def get_pending_messages(prof_id: int = None) -> list:
    with get_cursor() as cur:
        if prof_id:
            cur.execute("""
                SELECT m.*, p.name as patient_name, p.phone as patient_phone
                FROM messages m JOIN patients p ON p.id = m.patient_id
                WHERE m.professional_id = %s
                  AND m.status = 'pending' AND m.direction = 'in'
                ORDER BY m.created_at DESC
            """, (prof_id,))
        else:
            cur.execute("""
                SELECT m.*, p.name as patient_name, p.phone as patient_phone,
                       pr.last_name as prof_last_name,
                       pr.first_name as prof_first_name
                FROM messages m
                JOIN patients p ON p.id = m.patient_id
                LEFT JOIN professionals pr ON pr.id = m.professional_id
                WHERE m.status = 'pending' AND m.direction = 'in'
                ORDER BY m.created_at DESC
            """)
        return cur.fetchall()

def mark_all_read(prof_id: int = None):
    with get_cursor() as cur:
        if prof_id:
            cur.execute("""
                UPDATE messages SET status = 'read', read_at = NOW()
                WHERE professional_id = %s AND status = 'pending'
            """, (prof_id,))
        else:
            cur.execute("""
                UPDATE messages SET status = 'read', read_at = NOW()
                WHERE status = 'pending'
            """)


# ═══════════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def log_notification(appointment_id: int, recipient_phone: str,
                     notif_type: str, status: str = "sent", error: str = None):
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO notifications
                (appointment_id, recipient_phone, type, status, sent_at, error_msg)
            VALUES (%s, %s, %s, %s,
                CASE WHEN %s = 'sent' THEN NOW() ELSE NULL END, %s)
        """, (appointment_id, recipient_phone, notif_type, status, status, error))


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTES
# ═══════════════════════════════════════════════════════════════════════════════

def get_report_by_month(year: int, month: int, prof_id: int = None) -> dict:
    with get_cursor() as cur:
        base = """
            SELECT COUNT(*) as total,
                   COUNT(DISTINCT a.patient_id) as unique_patients
            FROM appointments a
            WHERE EXTRACT(YEAR  FROM a.date) = %s
              AND EXTRACT(MONTH FROM a.date) = %s
              AND a.status = 'active'
        """
        if prof_id:
            cur.execute(base + " AND a.professional_id = %s", (year, month, prof_id))
        else:
            cur.execute(base, (year, month))
        summary = cur.fetchone()

        detail_q = """
            SELECT a.date, a.time,
                   p.name as patient_name, p.obra_social,
                   pr.last_name  as prof_last_name,
                   pr.first_name as prof_first_name
            FROM appointments a
            JOIN patients      p  ON p.id  = a.patient_id
            JOIN professionals pr ON pr.id = a.professional_id
            WHERE EXTRACT(YEAR  FROM a.date) = %s
              AND EXTRACT(MONTH FROM a.date) = %s
              AND a.status = 'active'
        """
        if prof_id:
            cur.execute(detail_q + " AND a.professional_id = %s ORDER BY a.date, a.time",
                        (year, month, prof_id))
        else:
            cur.execute(detail_q + " ORDER BY a.date, a.time", (year, month))
        detail = cur.fetchall()

        return {"summary": summary, "detail": detail}


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTES POR RANGO DE FECHAS
# ═══════════════════════════════════════════════════════════════════════════════

def get_report_by_range(desde: str, hasta: str, prof_id: int = None) -> dict:
    """Reporte por rango de fechas ISO (YYYY-MM-DD)."""
    with get_cursor() as cur:
        base = """
            SELECT COUNT(*) as total,
                   COUNT(DISTINCT a.patient_id) as unique_patients
            FROM appointments a
            WHERE a.date BETWEEN %s AND %s
              AND a.status = 'active'
        """
        if prof_id:
            cur.execute(base + " AND a.professional_id = %s", (desde, hasta, prof_id))
        else:
            cur.execute(base, (desde, hasta))
        summary = cur.fetchone()

        detail_q = """
            SELECT a.date, a.time,
                   p.name as patient_name, p.obra_social,
                   pr.last_name  as prof_last_name,
                   pr.first_name as prof_first_name
            FROM appointments a
            JOIN patients      p  ON p.id  = a.patient_id
            JOIN professionals pr ON pr.id = a.professional_id
            WHERE a.date BETWEEN %s AND %s
              AND a.status = 'active'
        """
        if prof_id:
            cur.execute(detail_q + " AND a.professional_id = %s ORDER BY a.date, a.time",
                        (desde, hasta, prof_id))
        else:
            cur.execute(detail_q + " ORDER BY a.date, a.time", (desde, hasta))
        detail = cur.fetchall()

        return {"summary": summary, "detail": detail}


def borrar_turnos_anteriores(hasta_fecha: str, prof_id: int = None):
    """Borra lógicamente turnos anteriores a una fecha (marca como 'deleted')."""
    with get_cursor() as cur:
        if prof_id:
            cur.execute("""
                UPDATE appointments
                SET status = 'deleted'
                WHERE date < %s AND professional_id = %s
                  AND status = 'active'
            """, (hasta_fecha, prof_id))
        else:
            cur.execute("""
                UPDATE appointments
                SET status = 'deleted'
                WHERE date < %s AND status = 'active'
            """, (hasta_fecha,))


def toggle_mensajes(prof_id: int, acepta: bool):
    with get_cursor() as cur:
        cur.execute("""
            UPDATE professionals SET acepta_mensajes = %s WHERE id = %s
        """, (acepta, prof_id))

def profesional_acepta_mensajes(prof_id: int) -> bool:
    with get_cursor() as cur:
        cur.execute("""
            SELECT acepta_mensajes FROM professionals WHERE id = %s
        """, (prof_id,))
        row = cur.fetchone()
        return row["acepta_mensajes"] if row else True
