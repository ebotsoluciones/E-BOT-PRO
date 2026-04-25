"""
handlers_admin.py — panel admin WhatsApp  E-BOT PRO 🦙🔥

Dos niveles de acceso:
  general      → ve todos los profesionales, reporte consolidado
  professional → ve solo su agenda

Estados admin:
  ADMIN                   → menú admin
  ADMIN_ELEGIR_PROF       → admin general elige qué profesional ver
  ADMIN_NUEVO_NOMBRE      → nombre del paciente (turno manual)
  ADMIN_NUEVO_DNI         → DNI del paciente
  ADMIN_NUEVO_OBRA        → obra social (paciente nuevo)
  ADMIN_NUEVO_FECHA       → fecha del turno
  ADMIN_NUEVO_HORA        → hora del turno
  ADMIN_CANCEL_FECHA      → fecha del turno a cancelar
  ADMIN_CANCEL_HORA       → hora del turno a cancelar
  BLOQUEAR_FECHA          → fecha a bloquear
  BLOQUEAR_HORA           → hora a bloquear
"""

from datetime import datetime
from db      import get_admin_by_phone, get_professional_by_id
from storage import get_user_state, set_user_state, set_user_states, clear_user
from services import (
    listar_profesionales, texto_lista_profesionales,
    turnos_del_dia, proximos_turnos,
    horarios_libres, generar_horarios_prof, normalizar_hora,
    slot_disponible, agregar_turno, cancelar_turno_por_slot,
    bloquear_horario, bloquear_dia_completo, horarios_para_bloquear,
    obtener_mensajes_pendientes, marcar_mensajes_leidos,
    texto_reporte,
    identificar_paciente_por_dni, registrar_paciente,
)


# ═══════════════════════════════════════════════════════════════════════════════
# MENÚS
# ═══════════════════════════════════════════════════════════════════════════════

MENU_ADMIN_PROF = """🛠 Panel admin

1️⃣ Turnos hoy
2️⃣ Próximos turnos
3️⃣ Mensajes
4️⃣ Nuevo turno
5️⃣ Cancelar turno
6️⃣ Bloquear agenda
7️⃣ Reporte del mes
8️⃣ Salir"""

MENU_ADMIN_GENERAL = """🛠 Admin general

1️⃣ Turnos hoy (elegir prof.)
2️⃣ Próximos turnos (elegir prof.)
3️⃣ Mensajes pendientes
4️⃣ Nuevo turno
5️⃣ Cancelar turno
6️⃣ Bloquear agenda
7️⃣ Reporte consolidado
8️⃣ Reporte por profesional
9️⃣ Salir"""


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRADA PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def manejar_admin(numero: str, body: str, msg):
    texto  = body.strip()
    admin  = get_admin_by_phone(numero)
    estado = get_user_state(numero, "estado", "ADMIN")

    if not admin:
        clear_user(numero)
        msg.body("⛔ Acceso no autorizado.")
        return

    es_general  = admin["role"] == "general"
    prof_id_adm = admin.get("professional_id")

    if estado == "ADMIN":
        _manejar_menu_admin(numero, texto, msg, es_general, prof_id_adm)
        return

    if estado == "ADMIN_ELEGIR_PROF":
        _elegir_profesional_admin(numero, texto, msg)
        return

    if estado == "ADMIN_NUEVO_NOMBRE":
        _nuevo_turno_nombre(numero, texto, msg)
        return

    if estado == "ADMIN_NUEVO_DNI":
        _nuevo_turno_dni(numero, texto, msg)
        return

    if estado == "ADMIN_NUEVO_OBRA":
        _nuevo_turno_obra(numero, texto, msg)
        return

    if estado == "ADMIN_NUEVO_FECHA":
        _nuevo_turno_fecha(numero, texto, msg)
        return

    if estado == "ADMIN_NUEVO_HORA":
        _nuevo_turno_hora(numero, texto, msg, es_general)
        return

    if estado == "ADMIN_CANCEL_FECHA":
        _cancel_fecha(numero, texto, msg)
        return

    if estado == "ADMIN_CANCEL_HORA":
        _cancel_hora(numero, texto, msg)
        return

    if estado == "BLOQUEAR_FECHA":
        _bloquear_fecha(numero, texto, msg)
        return

    if estado == "BLOQUEAR_HORA":
        _bloquear_hora(numero, texto, msg)
        return

    menu = MENU_ADMIN_GENERAL if es_general else MENU_ADMIN_PROF
    msg.body(menu)


# ═══════════════════════════════════════════════════════════════════════════════
# MENÚ PRINCIPAL ADMIN
# ═══════════════════════════════════════════════════════════════════════════════

def _manejar_menu_admin(numero: str, texto: str, msg, es_general: bool, prof_id_adm):

    # ── Admin de profesional ──────────────────────────────────────────────────
    if not es_general:
        prof_id = prof_id_adm

        if texto == "1":
            _mostrar_turnos_hoy(prof_id, msg)
        elif texto == "2":
            _mostrar_proximos(prof_id, msg)
        elif texto == "3":
            _mostrar_mensajes(prof_id, msg)
        elif texto == "3r":
            marcar_mensajes_leidos(prof_id)
            msg.body("✅ Mensajes marcados como leídos.")
        elif texto == "4":
            set_user_states(numero, {"adm_prof_id": prof_id, "estado": "ADMIN_NUEVO_NOMBRE"})
            msg.body("Nombre del paciente:")
        elif texto == "5":
            set_user_states(numero, {"adm_prof_id": prof_id, "estado": "ADMIN_CANCEL_FECHA"})
            msg.body("Fecha del turno a cancelar (dd/mm/yyyy):")
        elif texto == "6":
            set_user_states(numero, {"adm_prof_id": prof_id, "estado": "BLOQUEAR_FECHA"})
            msg.body("Fecha a bloquear (dd/mm/yyyy):")
        elif texto == "7":
            msg.body(texto_reporte(prof_id))
        elif texto == "8":
            clear_user(numero)
            msg.body("Hasta luego 👋\n_Panel admin cerrado._")
        else:
            msg.body(MENU_ADMIN_PROF)
        return

    # ── Admin general ─────────────────────────────────────────────────────────
    if texto in ["1", "2", "4", "5", "6"]:
        set_user_states(numero, {
            "adm_accion_pendiente": texto,
            "estado": "ADMIN_ELEGIR_PROF",
        })
        msg.body("¿Para qué profesional?\n\n" + texto_lista_profesionales())
        return

    if texto == "3":
        _mostrar_mensajes(None, msg)
        return

    if texto == "3r":
        marcar_mensajes_leidos(None)
        msg.body("✅ Mensajes marcados como leídos.")
        return

    if texto == "7":
        msg.body(texto_reporte(None))
        return

    if texto == "8":
        set_user_states(numero, {
            "adm_accion_pendiente": "reporte_prof",
            "estado": "ADMIN_ELEGIR_PROF",
        })
        msg.body("¿Reporte de qué profesional?\n\n" + texto_lista_profesionales())
        return

    if texto == "9":
        clear_user(numero)
        msg.body("Hasta luego 👋\n_Panel admin cerrado._")
        return

    msg.body(MENU_ADMIN_GENERAL)


def _elegir_profesional_admin(numero: str, texto: str, msg):
    profs = listar_profesionales()
    try:
        idx  = int(texto.strip()) - 1
        prof = profs[idx]
    except (ValueError, IndexError):
        msg.body("❌ Opción inválida.\n\n" + texto_lista_profesionales())
        return

    prof_id = prof["id"]
    accion  = get_user_state(numero, "adm_accion_pendiente")
    set_user_state(numero, "adm_prof_id", prof_id)

    if accion == "1":
        _mostrar_turnos_hoy(prof_id, msg)
        set_user_state(numero, "estado", "ADMIN")

    elif accion == "2":
        _mostrar_proximos(prof_id, msg)
        set_user_state(numero, "estado", "ADMIN")

    elif accion == "4":
        set_user_state(numero, "estado", "ADMIN_NUEVO_NOMBRE")
        msg.body("Nombre del paciente:")

    elif accion == "5":
        set_user_state(numero, "estado", "ADMIN_CANCEL_FECHA")
        msg.body("Fecha del turno a cancelar (dd/mm/yyyy):")

    elif accion == "6":
        set_user_state(numero, "estado", "BLOQUEAR_FECHA")
        msg.body("Fecha a bloquear (dd/mm/yyyy):")

    elif accion == "reporte_prof":
        msg.body(texto_reporte(prof_id))
        set_user_state(numero, "estado", "ADMIN")


# ═══════════════════════════════════════════════════════════════════════════════
# TURNOS HOY / PRÓXIMOS
# ═══════════════════════════════════════════════════════════════════════════════

def _mostrar_turnos_hoy(prof_id: int, msg):
    hoy   = datetime.now().strftime("%d/%m/%Y")
    lista = turnos_del_dia(prof_id)
    prof  = get_professional_by_id(prof_id)
    nombre_prof = f"{prof['last_name']}, {prof['first_name']}" if prof else "—"

    if not lista:
        msg.body(f"Sin turnos para hoy ({hoy}).")
        return

    lineas = []
    for t in lista:
        hora  = t["time"].strftime("%H:%M")
        obra  = f" [{t['obra_social']}]" if t.get("obra_social") else ""
        lineas.append(f"🕐 {hora}  {t['patient_name']}{obra}")

    msg.body(
        f"📋 Turnos de hoy — {hoy}\n"
        f"👨‍⚕️ {nombre_prof}\n" +
        "─" * 25 + "\n" +
        "\n".join(lineas) + "\n" +
        "─" * 25 +
        f"\nTotal: {len(lista)} turno(s)"
    )


def _mostrar_proximos(prof_id: int, msg):
    prof    = get_professional_by_id(prof_id)
    nombre_prof = f"{prof['last_name']}, {prof['first_name']}" if prof else "—"
    futuros = proximos_turnos(prof_id)

    if not futuros:
        msg.body("Sin turnos próximos.")
        return

    lineas = []
    for t in futuros:
        fecha = t["date"].strftime("%d/%m/%Y")
        hora  = t["time"].strftime("%H:%M")
        lineas.append(f"📅 {fecha}  🕐 {hora}  👤 {t['patient_name']}")

    msg.body(
        f"📋 Próximos turnos — {nombre_prof}\n" +
        "─" * 25 + "\n" +
        "\n".join(lineas) + "\n" +
        "─" * 25 +
        f"\nTotal: {len(futuros)} turno(s)"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# MENSAJES
# ═══════════════════════════════════════════════════════════════════════════════

def _mostrar_mensajes(prof_id, msg):
    mensajes = obtener_mensajes_pendientes(prof_id)

    if not mensajes:
        msg.body("Sin mensajes pendientes. ✅")
        return

    lineas = []
    for m in mensajes:
        tel   = (m["patient_phone"] or "").replace("whatsapp:+", "+")
        fecha = m["created_at"].strftime("%d/%m %H:%M") if m.get("created_at") else ""
        prof_tag = ""
        if m.get("prof_last_name"):
            prof_tag = f"  [{m['prof_last_name']}, {m['prof_first_name']}]"
        lineas.append(
            f"👤 {m['patient_name']} — {tel}{prof_tag}\n"
            f"💬 {m['content']}\n"
            f"🕐 {fecha}"
        )

    msg.body(
        f"📨 Mensajes pendientes\n" +
        "─" * 25 + "\n" +
        "\n\n".join(lineas) + "\n" +
        "─" * 25 +
        f"\nTotal: {len(mensajes)}\n\n"
        "Escribí *3r* para marcar todos como leídos."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# NUEVO TURNO (admin)
# ═══════════════════════════════════════════════════════════════════════════════

def _nuevo_turno_nombre(numero: str, texto: str, msg):
    if len(texto.strip()) < 3:
        msg.body("❌ Ingresá el nombre completo:")
        return
    set_user_states(numero, {
        "adm_nombre": texto.strip().title(),
        "estado":     "ADMIN_NUEVO_DNI",
    })
    msg.body("DNI del paciente (sin puntos):")


def _nuevo_turno_dni(numero: str, texto: str, msg):
    dni = texto.strip().replace(".", "").replace("-", "")
    if not dni.isdigit() or len(dni) < 7:
        msg.body("❌ DNI inválido. Solo números:")
        return

    paciente = identificar_paciente_por_dni(dni)
    if paciente:
        set_user_states(numero, {
            "adm_patient_id": paciente["id"],
            "adm_dni":        dni,
            "estado":         "ADMIN_NUEVO_FECHA",
        })
        obra = paciente.get("obra_social") or "sin obra social"
        msg.body(
            f"Paciente: *{paciente['name']}*\n"
            f"Obra social: {obra}\n\n"
            f"Fecha del turno (dd/mm/yyyy):"
        )
    else:
        # Paciente nuevo — pedir obra social
        set_user_states(numero, {
            "adm_dni":    dni,
            "estado":     "ADMIN_NUEVO_OBRA",
        })
        msg.body(
            f"Paciente nuevo: *{get_user_state(numero, 'adm_nombre')}*\n"
            f"¿Tiene obra social? Escribí el nombre o *no*:"
        )


def _nuevo_turno_obra(numero: str, texto: str, msg):
    obra_social = None if texto.lower() in ["no", "no tengo", "-"] else texto.strip()
    nombre = get_user_state(numero, "adm_nombre")
    dni    = get_user_state(numero, "adm_dni")

    paciente = registrar_paciente("", nombre, dni, obra_social)
    set_user_states(numero, {
        "adm_patient_id": paciente["id"],
        "estado":         "ADMIN_NUEVO_FECHA",
    })
    msg.body(
        f"✅ Paciente registrado: *{nombre}*\n\n"
        f"Fecha del turno (dd/mm/yyyy):"
    )


def _nuevo_turno_fecha(numero: str, texto: str, msg):
    try:
        fecha = datetime.strptime(texto.strip(), "%d/%m/%Y").date()
    except ValueError:
        msg.body("❌ Formato inválido. Usá dd/mm/yyyy:")
        return

    fecha_str = fecha.strftime("%d/%m/%Y")
    prof_id   = get_user_state(numero, "adm_prof_id")
    libres    = horarios_libres(prof_id, fecha_str)

    if not libres:
        msg.body(f"Sin horarios disponibles para el {fecha_str}. Otra fecha:")
        return

    set_user_states(numero, {
        "adm_fecha": fecha_str,
        "estado":    "ADMIN_NUEVO_HORA",
    })
    msg.body("Horarios disponibles:\n\n" + "\n".join(libres) + "\n\n¿Qué hora?")


def _nuevo_turno_hora(numero: str, texto: str, msg, es_general: bool):
    hora       = normalizar_hora(texto)
    prof_id    = get_user_state(numero, "adm_prof_id")
    fecha      = get_user_state(numero, "adm_fecha")
    patient_id = get_user_state(numero, "adm_patient_id")

    if hora is None:
        msg.body("❌ Hora inválida. Usá HH:MM:")
        return

    disponible, motivo = slot_disponible(prof_id, fecha, hora)
    if not disponible:
        msg.body(f"❌ Ese horario está {motivo}. Elegí otro:")
        return

    agregar_turno(prof_id, patient_id, fecha, hora, created_by="admin")
    prof = get_professional_by_id(prof_id)
    nombre_prof = f"{prof['last_name']}, {prof['first_name']}" if prof else "—"
    msg.body(
        f"✅ Turno creado\n"
        f"📅 {fecha} a las {hora} hs\n"
        f"👨‍⚕️ {nombre_prof}"
    )
    set_user_state(numero, "estado", "ADMIN")


# ═══════════════════════════════════════════════════════════════════════════════
# CANCELAR TURNO (admin)
# ═══════════════════════════════════════════════════════════════════════════════

def _cancel_fecha(numero: str, texto: str, msg):
    try:
        fecha = datetime.strptime(texto.strip(), "%d/%m/%Y").date()
    except ValueError:
        msg.body("❌ Formato inválido. Usá dd/mm/yyyy:")
        return

    fecha_str = fecha.strftime("%d/%m/%Y")
    prof_id   = get_user_state(numero, "adm_prof_id")
    lista     = turnos_del_dia(prof_id, fecha_str)

    if not lista:
        msg.body(f"No hay turnos el {fecha_str}.")
        set_user_state(numero, "estado", "ADMIN")
        return

    set_user_states(numero, {
        "adm_cancel_fecha": fecha_str,
        "estado":           "ADMIN_CANCEL_HORA",
    })
    lineas = [
        f"{t['time'].strftime('%H:%M')} — {t['patient_name']}"
        for t in lista
    ]
    msg.body(
        f"Turnos del {fecha_str}:\n\n" +
        "\n".join(lineas) +
        "\n\n¿Qué hora cancelar? (HH:MM)"
    )


def _cancel_hora(numero: str, texto: str, msg):
    hora    = normalizar_hora(texto)
    fecha   = get_user_state(numero, "adm_cancel_fecha")
    prof_id = get_user_state(numero, "adm_prof_id")

    if hora is None:
        msg.body("❌ Hora inválida. Usá HH:MM:")
        return

    turno = cancelar_turno_por_slot(prof_id, fecha, hora, cancelled_by="admin")
    if turno:
        msg.body(f"✅ Turno cancelado: {fecha} {hora} hs — {turno['patient_name']}")
    else:
        msg.body("❌ No se encontró ese turno.")

    set_user_state(numero, "estado", "ADMIN")


# ═══════════════════════════════════════════════════════════════════════════════
# BLOQUEAR AGENDA
# ═══════════════════════════════════════════════════════════════════════════════

def _bloquear_fecha(numero: str, texto: str, msg):
    try:
        fecha = datetime.strptime(texto.strip(), "%d/%m/%Y").date()
    except ValueError:
        msg.body("❌ Formato inválido. Usá dd/mm/yyyy:")
        return

    fecha_str = fecha.strftime("%d/%m/%Y")
    prof_id   = get_user_state(numero, "adm_prof_id")
    horarios  = horarios_para_bloquear(prof_id, fecha_str)

    if not horarios:
        msg.body(f"✅ Todos los horarios del {fecha_str} ya están bloqueados.")
        set_user_state(numero, "estado", "ADMIN")
        return

    set_user_states(numero, {
        "bloqueo_fecha": fecha_str,
        "estado":        "BLOQUEAR_HORA",
    })
    msg.body(
        f"Horarios disponibles del {fecha_str}:\n\n" +
        "\n".join(horarios) +
        "\n\n¿Qué hora bloquear?\n"
        "Escribí la hora (HH:MM) o *todos* para bloquear el día completo."
    )


def _bloquear_hora(numero: str, texto: str, msg):
    fecha   = get_user_state(numero, "bloqueo_fecha")
    prof_id = get_user_state(numero, "adm_prof_id")

    if texto.strip().lower() == "todos":
        bloquear_dia_completo(prof_id, fecha)
        msg.body(f"✅ Día {fecha} bloqueado completo.")
    else:
        hora = normalizar_hora(texto)
        if hora is None:
            msg.body("❌ Hora inválida. Usá HH:MM o escribí *todos*:")
            return
        bloquear_horario(prof_id, fecha, hora)
        msg.body(f"✅ Bloqueado: {fecha} {hora} hs")

    set_user_state(numero, "estado", "ADMIN")
