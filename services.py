"""
services.py — lógica de negocio E-BOT PRO 🦙🔥

Diferencias respecto a LITE:
  - Todas las operaciones reciben professional_id
  - Horarios vienen de schedule_config en DB (no de variables de entorno)
  - Pacientes tienen perfil propio (dni, obra_social, plan)
  - Identificación por teléfono con fallback por DNI
  - Mensajes tienen estado pending/read en lugar de borrado
"""

from datetime import datetime, timedelta
from db import (
    # profesionales
    get_professionals, get_professional_by_id,
    # pacientes
    get_patient_by_phone, get_patient_by_dni, create_patient, update_patient_phone,
    # agenda
    get_schedule_for_day, get_blocked_slots, is_slot_blocked,
    block_slot, get_upcoming_appointments,
    # turnos
    get_appointments_by_date, get_patient_appointments,
    is_slot_taken, create_appointment, cancel_appointment,
    get_appointment_by_slot, get_report_by_month,
    # mensajes
    save_message, get_pending_messages, mark_all_read,
    # notificaciones
    log_notification,
)
from notifications import (
    notif_paciente_confirmado,
    notif_paciente_cancelado,
    notif_admin_nuevo_turno,
    notif_admin_cancelado,
)


# ═══════════════════════════════════════════════════════════════════════════════
# PROFESIONALES
# ═══════════════════════════════════════════════════════════════════════════════

def listar_profesionales() -> list:
    """Retorna todos los profesionales activos."""
    return get_professionals(active_only=True)

def texto_lista_profesionales() -> str:
    """Genera el texto de selección para el paciente."""
    profs = listar_profesionales()
    if not profs:
        return "No hay profesionales disponibles en este momento."
    lineas = [f"{i+1} {p['last_name']}, {p['first_name']}" + (f" — {p['specialty']}" if p.get('specialty') else "")
              for i, p in enumerate(profs)]
    return "\n".join(lineas)
              




# ═══════════════════════════════════════════════════════════════════════════════
# HORARIOS — basados en schedule_config de la DB
# ═══════════════════════════════════════════════════════════════════════════════

def generar_horarios_prof(prof_id: int, fecha_str: str) -> list[str]:
    """
    Genera los slots del día según la configuración de agenda del profesional.
    Retorna lista vacía si no trabaja ese día.
    """
    try:
        fecha = datetime.strptime(fecha_str, "%d/%m/%Y").date()
    except ValueError:
        return []

    # 0=lunes, 6=domingo (Python weekday())
    day_of_week = fecha.weekday()
    config = get_schedule_for_day(prof_id, day_of_week)

    if not config:
        return []

    slots = []
    actual = datetime.combine(fecha, config["start_time"])
    fin    = datetime.combine(fecha, config["end_time"])
    delta  = timedelta(minutes=config["slot_minutes"])

    while actual <= fin:
        slots.append(actual.strftime("%H:%M"))
        actual += delta

    return slots

def normalizar_hora(texto: str):
    texto = texto.strip().replace(".", ":").replace("-", ":")
    if ":" not in texto:
        texto += ":00"
    partes = texto.split(":")
    try:
        h, m = int(partes[0]), int(partes[1])
        return f"{h:02d}:{m:02d}"
    except Exception:
        return None

def horarios_libres(prof_id: int, fecha_str: str) -> list[str]:
    """Slots disponibles: generados - ocupados - bloqueados."""
    todos    = generar_horarios_prof(prof_id, fecha_str)
    if not todos:
        return []

    try:
        fecha_date = datetime.strptime(fecha_str, "%d/%m/%Y").date()
    except ValueError:
        return []

    fecha_iso = fecha_date.isoformat()

    ocupados  = {
        t["time"].strftime("%H:%M")
        for t in get_appointments_by_date(prof_id, fecha_iso)
    }
    bloqueados_raw = get_blocked_slots(prof_id, fecha_iso)
    bloqueados = set()
    for b in bloqueados_raw:
        t_from = datetime.combine(fecha_date, b["time_from"])
        t_to   = datetime.combine(fecha_date, b["time_to"])
        slot   = t_from
        while slot < t_to:
            bloqueados.add(slot.strftime("%H:%M"))
            slot += timedelta(minutes=30)

    return [h for h in todos if h not in ocupados and h not in bloqueados]

def horarios_para_bloquear(prof_id: int, fecha_str: str) -> list[str]:
    """Slots que aún no están bloqueados para esa fecha."""
    todos = generar_horarios_prof(prof_id, fecha_str)
    if not todos:
        return []

    try:
        fecha_iso = datetime.strptime(fecha_str, "%d/%m/%Y").date().isoformat()
    except ValueError:
        return []

    bloqueados_raw = get_blocked_slots(prof_id, fecha_iso)
    bloqueados = set()
    for b in bloqueados_raw:
        fecha_date = datetime.strptime(fecha_str, "%d/%m/%Y").date()
        t_from = datetime.combine(fecha_date, b["time_from"])
        t_to   = datetime.combine(fecha_date, b["time_to"])
        slot   = t_from
        while slot < t_to:
            bloqueados.add(slot.strftime("%H:%M"))
            slot += timedelta(minutes=30)

    return [h for h in todos if h not in bloqueados]


# ═══════════════════════════════════════════════════════════════════════════════
# PACIENTES — identificación y registro
# ═══════════════════════════════════════════════════════════════════════════════

def identificar_paciente_por_telefono(phone: str) -> dict | None:
    """Busca paciente por teléfono. None si no existe."""
    return get_patient_by_phone(phone)

def identificar_paciente_por_dni(dni: str) -> dict | None:
    """Busca paciente por DNI. None si no existe."""
    dni_limpio = dni.strip().replace(".", "").replace("-", "")
    return get_patient_by_dni(dni_limpio)

def registrar_paciente(phone: str, name: str, dni: str,
                       obra_social: str = None, plan: str = None) -> dict:
    """Crea un paciente nuevo."""
    dni_limpio = dni.strip().replace(".", "").replace("-", "")
    return create_patient(phone, name.strip().title(), dni_limpio, obra_social, plan)

def vincular_telefono(patient_id: int, phone: str):
    """Asocia un nuevo teléfono a un paciente existente (identificado por DNI)."""
    update_patient_phone(patient_id, phone)

def texto_confirmar_perfil(paciente: dict) -> str:
    """Texto para que el paciente confirme si el perfil encontrado es suyo."""
    obra = paciente.get("obra_social") or "sin obra social"
    return (
        f"👤 Encontramos este perfil:\n"
        f"*{paciente['name']}*\n"
        f"DNI: {paciente['dni']}\n"
        f"Obra social: {obra}\n\n"
        f"¿Sos vos? (S/N)"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TURNOS
# ═══════════════════════════════════════════════════════════════════════════════

def agregar_turno(prof_id: int, patient_id: int, fecha_str: str, hora: str,
                  created_by: str = "patient") -> dict:
    """
    Crea el turno, notifica al paciente y al admin del profesional.
    Retorna el turno creado.
    """
    from db import get_patient_by_id, get_admin_by_phone, get_professional_by_id
    from db import get_conn

    fecha_iso = datetime.strptime(fecha_str, "%d/%m/%Y").date().isoformat()
    hora_db   = hora + ":00" if len(hora) == 5 else hora

    turno    = create_appointment(prof_id, patient_id, fecha_iso, hora_db, created_by)
    paciente = get_patient_by_id(patient_id)
    prof     = get_professional_by_id(prof_id)

    # Notificación al paciente
    if paciente and paciente.get("phone"):
        notif_paciente_confirmado(
            paciente["phone"], paciente["name"], fecha_str, hora,
            prof["name"] if prof else None
        )
        log_notification(turno["id"], paciente["phone"], "confirmed", "sent")

    # Notificación al admin del profesional
    if prof and prof.get("phone"):
        notif_admin_nuevo_turno(
            paciente["name"] if paciente else "Paciente",
            paciente["phone"] if paciente else "",
            fecha_str, hora
        )
        log_notification(turno["id"], prof["phone"], "confirmed_admin", "sent")

    return turno

def cancelar_turno_por_slot(prof_id: int, fecha_str: str, hora: str,
                            cancelled_by: str = "patient") -> dict | None:
    """
    Cancela un turno por fecha/hora. Notifica al paciente y al admin.
    Retorna el turno cancelado o None si no existía.
    """
    from db import get_patient_by_id, get_professional_by_id

    fecha_iso = datetime.strptime(fecha_str, "%d/%m/%Y").date().isoformat()
    hora_db   = hora + ":00" if len(hora) == 5 else hora

    turno = get_appointment_by_slot(prof_id, fecha_iso, hora_db)
    if not turno:
        return None

    cancel_appointment(turno["id"], cancelled_by)

    paciente = get_patient_by_id(turno["patient_id"])
    prof     = get_professional_by_id(prof_id)

    if paciente and paciente.get("phone"):
        notif_paciente_cancelado(
            paciente["phone"], paciente["name"], fecha_str, hora,
            prof["name"] if prof else None
        )

    if prof and prof.get("phone"):
        notif_admin_cancelado(
            paciente["name"] if paciente else "Paciente",
            paciente["phone"] if paciente else "",
            fecha_str, hora
        )

    return turno

def turnos_del_dia(prof_id: int, fecha_str: str = None) -> list:
    """Turnos activos de un profesional para una fecha (default: hoy)."""
    if fecha_str is None:
        fecha_str = datetime.now().strftime("%d/%m/%Y")
    fecha_iso = datetime.strptime(fecha_str, "%d/%m/%Y").date().isoformat()
    return get_appointments_by_date(prof_id, fecha_iso)

def proximos_turnos(prof_id: int) -> list:
    """Turnos futuros activos de un profesional."""
    return get_upcoming_appointments(prof_id)

def mis_turnos_paciente(patient_id: int) -> list:
    """Turnos futuros activos de un paciente."""
    return get_patient_appointments(patient_id)


# ═══════════════════════════════════════════════════════════════════════════════
# BLOQUEOS
# ═══════════════════════════════════════════════════════════════════════════════

def bloquear_horario(prof_id: int, fecha_str: str, hora: str, created_by: str = None):
    """Bloquea un slot de 1 hora (time_from = hora, time_to = hora + slot)."""
    fecha_iso = datetime.strptime(fecha_str, "%d/%m/%Y").date().isoformat()
    t_from    = datetime.strptime(hora, "%H:%M")
    t_to      = t_from + timedelta(minutes=60)
    block_slot(
        prof_id, fecha_iso,
        t_from.strftime("%H:%M:%S"),
        t_to.strftime("%H:%M:%S"),
        created_by=created_by
    )

def bloquear_dia_completo(prof_id: int, fecha_str: str, created_by: str = None):
    """Bloquea todos los horarios de un día."""
    for hora in generar_horarios_prof(prof_id, fecha_str):
        bloquear_horario(prof_id, fecha_str, hora, created_by)

def slot_disponible(prof_id: int, fecha_str: str, hora: str) -> tuple[bool, str]:
    """
    Verifica si un slot está disponible.
    Retorna (disponible: bool, motivo: str)
    """
    fecha_iso = datetime.strptime(fecha_str, "%d/%m/%Y").date().isoformat()
    hora_db   = hora + ":00" if len(hora) == 5 else hora

    if is_slot_blocked(prof_id, fecha_iso, hora_db):
        return False, "bloqueado"
    if is_slot_taken(prof_id, fecha_iso, hora_db):
        return False, "ocupado"
    return True, "disponible"


# ═══════════════════════════════════════════════════════════════════════════════
# MENSAJES
# ═══════════════════════════════════════════════════════════════════════════════

def guardar_mensaje(patient_id: int, contenido: str, prof_id: int = None):
    """Guarda un mensaje entrante del paciente."""
    save_message(patient_id, contenido, prof_id, direction="in")

def obtener_mensajes_pendientes(prof_id: int = None) -> list:
    """
    Mensajes pendientes de un profesional, o todos si prof_id es None
    (para el admin general).
    """
    return get_pending_messages(prof_id)

def marcar_mensajes_leidos(prof_id: int = None):
    """Marca como leídos todos los mensajes pendientes."""
    mark_all_read(prof_id)


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTES
# ═══════════════════════════════════════════════════════════════════════════════

def reporte_mes(prof_id: int = None, año: int = None, mes: int = None) -> dict:
    """
    Reporte del mes. Si prof_id es None devuelve el consolidado de la clínica.
    """
    hoy  = datetime.now()
    año  = año  or hoy.year
    mes  = mes  or hoy.month
    return get_report_by_month(año, mes, prof_id)

def texto_reporte(prof_id: int = None) -> str:
    """Genera el texto del reporte para enviar por WhatsApp."""
    from db import get_professional_by_id
    hoy    = datetime.now()
    data   = reporte_mes(prof_id)
    resumen = data["summary"]
    detalle = data["detail"]

    titulo = "📊 Reporte — "
    if prof_id:
        prof    = get_professional_by_id(prof_id)
        titulo += f"{prof['name']} — " if prof else ""
    else:
        titulo += "Clínica — "
    titulo += hoy.strftime("%B %Y").capitalize()

    lineas = [
        titulo,
        "─" * 25,
        f"Turnos del mes: {resumen['total']}",
        f"Pacientes únicos: {resumen['unique_patients']}",
        "─" * 25,
    ]

    if detalle:
        for t in detalle:
            fecha = t["date"].strftime("%d/%m/%Y")
            hora  = t["time"].strftime("%H:%M")
            prof_nombre = t.get("professional_name", "")
            lineas.append(f"📅 {fecha}  🕐 {hora}  👤 {t['patient_name']}" +
                          (f"  ({prof_nombre})" if not prof_id and prof_nombre else ""))
    else:
        lineas.append("Sin turnos este mes.")

    return "\n".join(lineas)
