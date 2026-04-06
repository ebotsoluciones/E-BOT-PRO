"""
handlers_paciente.py — flujo conversacional del paciente E-BOT PRO 🦙🔥

Estados del paciente:
  MENU                  → menú principal
  CONFIRMAR_PERFIL      → ¿Sos vos? S/N
  PERFIL_DNI            → ingresá tu DNI (fallback por DNI)
  PERFIL_NOMBRE         → ingresá nombre y apellido (paciente nuevo)
  PERFIL_DNI_NUEVO      → ingresá DNI (paciente nuevo)
  PERFIL_OBRA_SOCIAL    → ingresá obra social (paciente nuevo)
  ELEGIR_PROFESIONAL    → elegí un profesional de la lista
  TURNO_FECHA           → ingresá fecha del turno
  TURNO_HORA            → elegí horario disponible
  CONFIRMAR_TURNO       → confirmás el turno? S/N
  MIS_TURNOS_CANCELAR   → elegí turno a cancelar
  MENSAJE               → escribí tu mensaje
"""

from datetime import datetime
from config   import NOMBRE_CLINICA
from storage  import get_user_state, set_user_state, set_user_states, clear_user
from services import (
    listar_profesionales, texto_lista_profesionales,
    identificar_paciente_por_telefono, identificar_paciente_por_dni,
    registrar_paciente, vincular_telefono, texto_confirmar_perfil,
    generar_horarios_prof, normalizar_hora,
    horarios_libres, slot_disponible,
    agregar_turno, cancelar_turno_por_slot,
    mis_turnos_paciente, guardar_mensaje,
)


# ═══════════════════════════════════════════════════════════════════════════════
# MENÚ PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def menu_paciente() -> str:
    return (
        f"🦙 {NOMBRE_CLINICA}\n\n"
        f"1 Sacar turno\n"
        f"2 Mis turnos\n"
        f"3 Cancelar turno\n"
        f"4 Mensaje\n"
        f"5 Urgencia\n"
        f"6 Salir"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRADA PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def manejar_paciente(numero: str, body: str, msg):
    texto  = body.strip()
    estado = get_user_state(numero, "estado", "MENU")

    # ── Reset global ──────────────────────────────────────────────────────────
    if texto.lower() in ["menu", "/start", "inicio"]:
        clear_user(numero)
        msg.body(menu_paciente())
        return

    # ── Router por estado ─────────────────────────────────────────────────────
    handlers = {
        "MENU":               _manejar_menu,
        "CONFIRMAR_PERFIL":   _confirmar_perfil,
        "PERFIL_DNI":         _perfil_dni_fallback,
        "PERFIL_NOMBRE":      _perfil_nombre_nuevo,
        "PERFIL_DNI_NUEVO":   _perfil_dni_nuevo,
        "PERFIL_OBRA_SOCIAL": _perfil_obra_social,
        "ELEGIR_PROFESIONAL": _elegir_profesional,
        "TURNO_FECHA":        _turno_fecha,
        "TURNO_HORA":         _turno_hora,
        "CONFIRMAR_TURNO":    _confirmar_turno,
        "MIS_TURNOS_CANCELAR":_cancelar_mi_turno,
        "MENSAJE":            _recibir_mensaje,
    }
    handler = handlers.get(estado)
    if handler:
        handler(numero, texto, msg)
    else:
        clear_user(numero)
        msg.body(menu_paciente())


# ═══════════════════════════════════════════════════════════════════════════════
# MENÚ
# ═══════════════════════════════════════════════════════════════════════════════

def _manejar_menu(numero: str, texto: str, msg):
    opciones = {
        "1": _iniciar_turno,
        "2": _ver_mis_turnos,
        "3": _iniciar_cancelar,
        "4": _iniciar_mensaje,
        "5": _urgencia,
        "6": _salir,
    }
    accion = opciones.get(texto)
    if accion:
        accion(numero, msg)
    else:
        msg.body(menu_paciente())


# ═══════════════════════════════════════════════════════════════════════════════
# IDENTIFICACIÓN DEL PACIENTE
# Flujo: teléfono → confirmar perfil → (N) → DNI → buscar → (nuevo) → registrar
# ═══════════════════════════════════════════════════════════════════════════════

def _resolver_identidad(numero: str, msg, destino_estado: str):
    """
    Verifica si el paciente ya tiene perfil.
    - Conocido → pide confirmación S/N
    - Desconocido → pide DNI para buscar o registrar
    El destino_estado es el estado al que ir una vez identificado.
    """
    set_user_state(numero, "destino_post_id", destino_estado)
    paciente = identificar_paciente_por_telefono(numero)

    if paciente:
        set_user_state(numero, "patient_id_temp", paciente["id"])
        set_user_state(numero, "estado", "CONFIRMAR_PERFIL")
        msg.body(texto_confirmar_perfil(paciente))
    else:
        set_user_state(numero, "estado", "PERFIL_DNI")
        msg.body("Para comenzar necesito tu DNI (sin puntos):")


def _confirmar_perfil(numero: str, texto: str, msg):
    """El paciente confirma si el perfil encontrado es suyo."""
    destino = get_user_state(numero, "destino_post_id", "ELEGIR_PROFESIONAL")

    if texto.lower() in ["s", "si", "sí", "yes"]:
        patient_id = get_user_state(numero, "patient_id_temp")
        set_user_states(numero, {
            "patient_id": patient_id,
            "patient_id_temp": None,
            "estado": destino,
        })
        _continuar_flujo(numero, destino, msg)

    elif texto.lower() in ["n", "no"]:
        set_user_state(numero, "estado", "PERFIL_DNI")
        msg.body("Ingresá tu DNI (sin puntos) para buscar tu perfil:")

    else:
        paciente = identificar_paciente_por_telefono(numero)
        msg.body(texto_confirmar_perfil(paciente) if paciente else menu_paciente())


def _perfil_dni_fallback(numero: str, texto: str, msg):
    """Busca paciente por DNI. Si no existe, inicia registro."""
    dni = texto.strip().replace(".", "").replace("-", "")
    if not dni.isdigit() or len(dni) < 7:
        msg.body("❌ DNI inválido. Ingresá solo números (ej: 28456789):")
        return

    paciente = identificar_paciente_por_dni(dni)
    destino  = get_user_state(numero, "destino_post_id", "ELEGIR_PROFESIONAL")

    if paciente:
        # Encontrado por DNI — actualizar teléfono y confirmar
        vincular_telefono(paciente["id"], numero)
        set_user_states(numero, {
            "patient_id": paciente["id"],
            "estado": destino,
        })
        msg.body(f"✅ Perfil encontrado. Hola {paciente['name'].split()[0]}!")
        _continuar_flujo(numero, destino, msg)
    else:
        # Paciente nuevo — iniciar registro
        set_user_states(numero, {
            "dni_temp": dni,
            "estado": "PERFIL_NOMBRE",
        })
        msg.body("No encontramos tu perfil. Vamos a crearlo.\n¿Cuál es tu nombre y apellido?")


def _perfil_nombre_nuevo(numero: str, texto: str, msg):
    if len(texto.strip()) < 3:
        msg.body("❌ Ingresá tu nombre completo:")
        return
    set_user_states(numero, {
        "nombre_temp": texto.strip().title(),
        "estado": "PERFIL_DNI_NUEVO",
    })
    msg.body("Tu DNI (sin puntos):")


def _perfil_dni_nuevo(numero: str, texto: str, msg):
    dni = texto.strip().replace(".", "").replace("-", "")
    if not dni.isdigit() or len(dni) < 7:
        msg.body("❌ DNI inválido. Solo números (ej: 28456789):")
        return

    # Verificar que el DNI no esté ya registrado
    existente = identificar_paciente_por_dni(dni)
    if existente:
        vincular_telefono(existente["id"], numero)
        destino = get_user_state(numero, "destino_post_id", "ELEGIR_PROFESIONAL")
        set_user_states(numero, {
            "patient_id": existente["id"],
            "estado": destino,
        })
        msg.body(f"✅ Perfil encontrado. Hola {existente['name'].split()[0]}!")
        _continuar_flujo(numero, destino, msg)
        return

    set_user_states(numero, {
        "dni_temp": dni,
        "estado": "PERFIL_OBRA_SOCIAL",
    })
    msg.body("¿Tenés obra social? Escribí el nombre o *no* si no tenés:")


def _perfil_obra_social(numero: str, texto: str, msg):
    obra_social = None if texto.lower() in ["no", "no tengo", "-"] else texto.strip()
    nombre      = get_user_state(numero, "nombre_temp")
    dni         = get_user_state(numero, "dni_temp")
    destino     = get_user_state(numero, "destino_post_id", "ELEGIR_PROFESIONAL")

    paciente = registrar_paciente(numero, nombre, dni, obra_social)
    set_user_states(numero, {
        "patient_id":   paciente["id"],
        "nombre_temp":  None,
        "dni_temp":     None,
        "estado":       destino,
    })
    msg.body(f"✅ Perfil creado. Bienvenido/a {nombre.split()[0]}!")
    _continuar_flujo(numero, destino, msg)


def _continuar_flujo(numero: str, destino: str, msg):
    """Dispara el siguiente paso del flujo una vez identificado el paciente."""
    if destino == "ELEGIR_PROFESIONAL":
        _mostrar_profesionales(numero, msg)
    elif destino == "MIS_TURNOS_CANCELAR":
        _mostrar_mis_turnos_para_cancelar(numero, msg)


# ═══════════════════════════════════════════════════════════════════════════════
# FLUJO: SACAR TURNO
# ═══════════════════════════════════════════════════════════════════════════════

def _iniciar_turno(numero: str, msg):
    _resolver_identidad(numero, msg, destino_estado="ELEGIR_PROFESIONAL")


def _mostrar_profesionales(numero: str, msg):
    profs = listar_profesionales()
    if not profs:
        msg.body("❌ No hay profesionales disponibles. Intentá más tarde.")
        clear_user(numero)
        return
    set_user_state(numero, "estado", "ELEGIR_PROFESIONAL")
    msg.body(
        "¿Con quién querés sacar turno?\n\n" +
        texto_lista_profesionales()
    )


def _elegir_profesional(numero: str, texto: str, msg):
    profs = listar_profesionales()
    try:
        idx   = int(texto.strip()) - 1
        prof  = profs[idx]
    except (ValueError, IndexError):
        msg.body("❌ Opción inválida.\n\n" + texto_lista_profesionales())
        return

    set_user_states(numero, {
        "prof_id":   prof["id"],
        "prof_nombre": prof["name"],
        "estado":    "TURNO_FECHA",
    })
    msg.body(
        f"Turno con *{prof['name']}*" +
        (f" — {prof['specialty']}" if prof.get("specialty") else "") +
        "\n\nIngresá la fecha (dd/mm/yyyy):"
    )


def _turno_fecha(numero: str, texto: str, msg):
    try:
        fecha = datetime.strptime(texto.strip(), "%d/%m/%Y").date()
    except ValueError:
        msg.body("❌ Formato inválido. Usá dd/mm/yyyy (ej: 15/05/2025):")
        return

    if fecha < datetime.now().date():
        msg.body("❌ Esa fecha ya pasó. Ingresá una fecha futura:")
        return

    fecha_str = fecha.strftime("%d/%m/%Y")
    prof_id   = get_user_state(numero, "prof_id")
    libres    = horarios_libres(prof_id, fecha_str)

    if not libres:
        msg.body(
            f"Sin horarios disponibles para el {fecha_str}.\n"
            "Probá con otra fecha (dd/mm/yyyy):"
        )
        return

    set_user_states(numero, {
        "turno_fecha": fecha_str,
        "estado":      "TURNO_HORA",
    })
    msg.body("Horarios disponibles:\n\n" + "\n".join(libres) + "\n\n¿Qué hora elegís?")


def _turno_hora(numero: str, texto: str, msg):
    hora    = normalizar_hora(texto)
    prof_id = get_user_state(numero, "prof_id")
    fecha   = get_user_state(numero, "turno_fecha")

    if hora is None:
        msg.body("❌ Formato inválido. Usá HH:MM (ej: 10:00):")
        return

    horarios = generar_horarios_prof(prof_id, fecha)
    if hora not in horarios:
        msg.body("❌ Hora inválida. Elegí un horario de la lista:")
        return

    disponible, motivo = slot_disponible(prof_id, fecha, hora)
    if not disponible:
        msg.body(
            f"❌ Ese horario está {motivo}. Elegí otro:" +
            "\n\n" + "\n".join(horarios_libres(prof_id, fecha))
        )
        return

    prof_nombre = get_user_state(numero, "prof_nombre")
    set_user_states(numero, {
        "turno_hora": hora,
        "estado":     "CONFIRMAR_TURNO",
    })
    msg.body(
        f"📅 *Resumen del turno*\n"
        f"Profesional: {prof_nombre}\n"
        f"Fecha: {fecha}\n"
        f"Hora: {hora} hs\n\n"
        f"¿Confirmás? (S/N)"
    )


def _confirmar_turno(numero: str, texto: str, msg):
    if texto.lower() in ["s", "si", "sí", "yes"]:
        prof_id    = get_user_state(numero, "prof_id")
        patient_id = get_user_state(numero, "patient_id")
        fecha      = get_user_state(numero, "turno_fecha")
        hora       = get_user_state(numero, "turno_hora")
        prof_nombre = get_user_state(numero, "prof_nombre")

        agregar_turno(prof_id, patient_id, fecha, hora, created_by="patient")
        msg.body(
            f"✅ *Turno confirmado*\n"
            f"📅 {fecha} a las {hora} hs\n"
            f"👨‍⚕️ {prof_nombre}\n\n"
            f"Te enviamos una confirmación. ¡Hasta el día del turno!"
        )
        clear_user(numero)

    elif texto.lower() in ["n", "no"]:
        set_user_state(numero, "estado", "TURNO_FECHA")
        msg.body("Turno cancelado. Ingresá otra fecha (dd/mm/yyyy):")

    else:
        prof_nombre = get_user_state(numero, "prof_nombre")
        fecha       = get_user_state(numero, "turno_fecha")
        hora        = get_user_state(numero, "turno_hora")
        msg.body(
            f"📅 {fecha} {hora} hs con {prof_nombre}\n"
            f"¿Confirmás? (S/N)"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# FLUJO: MIS TURNOS
# ═══════════════════════════════════════════════════════════════════════════════

def _ver_mis_turnos(numero: str, msg):
    paciente = identificar_paciente_por_telefono(numero)
    if not paciente:
        msg.body("No encontramos tu perfil. Primero sacá un turno.")
        return

    turnos = mis_turnos_paciente(paciente["id"])
    if not turnos:
        msg.body("No tenés turnos próximos.")
        return

    lineas = []
    for t in turnos:
        fecha = t["date"].strftime("%d/%m/%Y")
        hora  = t["time"].strftime("%H:%M")
        lineas.append(f"📅 {fecha}  🕐 {hora}  👨‍⚕️ {t['professional_name']}")
    msg.body("Tus próximos turnos:\n\n" + "\n".join(lineas))


# ═══════════════════════════════════════════════════════════════════════════════
# FLUJO: CANCELAR TURNO
# ═══════════════════════════════════════════════════════════════════════════════

def _iniciar_cancelar(numero: str, msg):
    _resolver_identidad(numero, msg, destino_estado="MIS_TURNOS_CANCELAR")


def _mostrar_mis_turnos_para_cancelar(numero: str, msg):
    patient_id = get_user_state(numero, "patient_id")
    turnos     = mis_turnos_paciente(patient_id)

    if not turnos:
        msg.body("No tenés turnos próximos para cancelar.")
        clear_user(numero)
        return

    lineas = []
    for i, t in enumerate(turnos):
        fecha = t["date"].strftime("%d/%m/%Y")
        hora  = t["time"].strftime("%H:%M")
        lineas.append(f"{i+1} — {fecha} {hora} hs  {t['professional_name']}")

    # Guardar lista para referenciar por número
    set_user_states(numero, {
        "turnos_cancelar": [
            {
                "prof_id": t["professional_id"],
                "fecha":   t["date"].strftime("%d/%m/%Y"),
                "hora":    t["time"].strftime("%H:%M"),
            }
            for t in turnos
        ],
        "estado": "MIS_TURNOS_CANCELAR",
    })
    msg.body(
        "¿Cuál turno querés cancelar?\n\n" +
        "\n".join(lineas) +
        "\n\nEscribí el número:"
    )


def _cancelar_mi_turno(numero: str, texto: str, msg):
    turnos = get_user_state(numero, "turnos_cancelar", [])
    try:
        idx   = int(texto.strip()) - 1
        turno = turnos[idx]
    except (ValueError, IndexError):
        msg.body("❌ Opción inválida. Escribí el número del turno:")
        return

    cancelar_turno_por_slot(
        turno["prof_id"], turno["fecha"], turno["hora"],
        cancelled_by="patient"
    )
    msg.body(
        f"✅ Turno cancelado:\n"
        f"📅 {turno['fecha']} a las {turno['hora']} hs\n\n"
        f"Podés sacar un nuevo turno cuando quieras."
    )
    clear_user(numero)


# ═══════════════════════════════════════════════════════════════════════════════
# MENSAJE / URGENCIA / SALIR
# ═══════════════════════════════════════════════════════════════════════════════

def _iniciar_mensaje(numero: str, msg):
    paciente = identificar_paciente_por_telefono(numero)
    if paciente:
        set_user_states(numero, {
            "patient_id": paciente["id"],
            "estado":     "MENSAJE",
        })
    else:
        set_user_state(numero, "estado", "MENSAJE")
    msg.body("Escribí tu mensaje y te respondemos a la brevedad:")


def _recibir_mensaje(numero: str, texto: str, msg):
    patient_id = get_user_state(numero, "patient_id")
    if patient_id:
        guardar_mensaje(patient_id, texto)
    msg.body("✅ Mensaje recibido. Te respondemos pronto.")
    set_user_state(numero, "estado", "MENU")


def _urgencia(numero: str, msg):
    msg.body("🚨 *Urgencias*\nComunicate al: +549000000000")


def _salir(numero: str, msg):
    clear_user(numero)
    msg.body("Hasta luego 👋")
