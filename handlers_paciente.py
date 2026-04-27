"""
handlers_paciente.py — flujo conversacional del paciente E-BOT PRO 🦙🔥

Estados:
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
from config import (
    NOMBRE_CLINICA, DIRECCION, TELEFONO,
    HORARIO_ATENCION, LINK_MAPS, TELEFONO_URGENCIAS,
)
from storage import get_user_state, set_user_state, set_user_states, clear_user
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
        f"🏥 *{NOMBRE_CLINICA}*\n\n"
        f"1️⃣ Sacar turno\n"
        f"2️⃣ Mis turnos\n"
        f"3️⃣ Cancelar turno\n"
        f"4️⃣ Mensaje\n"
        f"5️⃣ Profesionales\n"
        f"6️⃣ Información\n"
        f"7️⃣ Salir"
    )

def bienvenida() -> str:
    return (
        f"👋 ¡Bienvenido/a a *{NOMBRE_CLINICA}*!\n\n"
        f"{LINK_MAPS}\n\n"
        f"Estamos aquí para ayudarle a gestionar sus turnos de forma sencilla.\n\n"
        f"Por favor, indicanos qué necesitás:\n\n"
        f"1️⃣ Sacar turno\n"
        f"2️⃣ Mis turnos\n"
        f"3️⃣ Cancelar turno\n"
        f"4️⃣ Mensaje\n"
        f"5️⃣ Profesionales\n"
        f"6️⃣ Información\n"
        f"7️⃣ Salir"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRADA PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def manejar_paciente(numero: str, body: str, msg):
    texto  = body.strip()
    estado = get_user_state(numero, "estado", "MENU")

    if texto.lower() in ["menu", "/start", "inicio"]:
        clear_user(numero)
        msg.body(bienvenida())
        return

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
        "MENSAJE":             _recibir_mensaje,
        "ELEGIR_PROF_MENSAJE": _elegir_prof_mensaje,
    }
    handler = handlers.get(estado)
    if handler:
        handler(numero, texto, msg)
    else:
        clear_user(numero)
        msg.body(bienvenida())


# ═══════════════════════════════════════════════════════════════════════════════
# MENÚ
# ═══════════════════════════════════════════════════════════════════════════════

def _manejar_menu(numero: str, texto: str, msg):
    es_nuevo = get_user_state(numero, "bienvenida_enviada", False)
    if not es_nuevo and texto.lower() not in ["1","2","3","4","5","6","7"]:
        set_user_state(numero, "bienvenida_enviada", True)
        msg.body(bienvenida())
        return

    opciones = {
        "1": _iniciar_turno,
        "2": _ver_mis_turnos,
        "3": _iniciar_cancelar,
        "4": _iniciar_mensaje,
        "5": _ver_profesionales,
        "6": _informacion,
        "7": _salir,
    }
    accion = opciones.get(texto)
    if accion:
        accion(numero, msg)
    else:
        msg.body(menu_paciente())


# ═══════════════════════════════════════════════════════════════════════════════
# IDENTIFICACIÓN DEL PACIENTE
# ═══════════════════════════════════════════════════════════════════════════════

def _resolver_identidad(numero: str, msg, destino_estado: str):
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
    destino = get_user_state(numero, "destino_post_id", "ELEGIR_PROFESIONAL")

    if texto.lower() in ["s", "si", "sí", "yes"]:
        patient_id = get_user_state(numero, "patient_id_temp")
        set_user_states(numero, {
            "patient_id":      patient_id,
            "patient_id_temp": None,
            "estado":          destino,
        })
        _continuar_flujo(numero, destino, msg)

    elif texto.lower() in ["n", "no"]:
        set_user_state(numero, "estado", "PERFIL_DNI")
        msg.body("Ingresá tu DNI (sin puntos) para buscar tu perfil:")

    else:
        paciente = identificar_paciente_por_telefono(numero)
        msg.body(texto_confirmar_perfil(paciente) if paciente else menu_paciente())


def _perfil_dni_fallback(numero: str, texto: str, msg):
    dni = texto.strip().replace(".", "").replace("-", "")
    if not dni.isdigit() or len(dni) < 7:
        msg.body("❌ DNI inválido. Ingresá solo números (ej: 28456789):")
        return

    paciente = identificar_paciente_por_dni(dni)
    destino  = get_user_state(numero, "destino_post_id", "ELEGIR_PROFESIONAL")

    if paciente:
        vincular_telefono(paciente["id"], numero)
        set_user_states(numero, {"patient_id": paciente["id"], "estado": destino})
        msg.body(f"✅ Perfil encontrado. Hola {paciente['name'].split()[0]}!")
        _continuar_flujo(numero, destino, msg)
    else:
        set_user_states(numero, {"dni_temp": dni, "estado": "PERFIL_NOMBRE"})
        msg.body("No encontramos tu perfil. Vamos a crearlo.\n¿Cuál es tu nombre y apellido?")


def _perfil_nombre_nuevo(numero: str, texto: str, msg):
    if len(texto.strip()) < 3:
        msg.body("❌ Ingresá tu nombre completo:")
        return
    set_user_states(numero, {"nombre_temp": texto.strip().title(), "estado": "PERFIL_DNI_NUEVO"})
    msg.body("Tu DNI (sin puntos):")


def _perfil_dni_nuevo(numero: str, texto: str, msg):
    dni = texto.strip().replace(".", "").replace("-", "")
    if not dni.isdigit() or len(dni) < 7:
        msg.body("❌ DNI inválido. Solo números (ej: 28456789):")
        return

    existente = identificar_paciente_por_dni(dni)
    if existente:
        vincular_telefono(existente["id"], numero)
        destino = get_user_state(numero, "destino_post_id", "ELEGIR_PROFESIONAL")
        set_user_states(numero, {"patient_id": existente["id"], "estado": destino})
        msg.body(f"✅ Perfil encontrado. Hola {existente['name'].split()[0]}!")
        _continuar_flujo(numero, destino, msg)
        return

    set_user_states(numero, {"dni_temp": dni, "estado": "PERFIL_OBRA_SOCIAL"})
    msg.body("¿Tenés obra social? Escribí el nombre o *no* si no tenés:")


def _perfil_obra_social(numero: str, texto: str, msg):
    obra_social = None if texto.lower() in ["no", "no tengo", "-"] else texto.strip()
    nombre  = get_user_state(numero, "nombre_temp")
    dni     = get_user_state(numero, "dni_temp")
    destino = get_user_state(numero, "destino_post_id", "ELEGIR_PROFESIONAL")

    paciente = registrar_paciente(numero, nombre, dni, obra_social)
    set_user_states(numero, {
        "patient_id":  paciente["id"],
        "nombre_temp": None,
        "dni_temp":    None,
        "estado":      destino,
    })
    msg.body(f"✅ Perfil creado. ¡Bienvenido/a {nombre.split()[0]}!")
    _continuar_flujo(numero, destino, msg)


def _continuar_flujo(numero: str, destino: str, msg):
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
    msg.body("¿Con quién querés sacar turno?\n\n" + texto_lista_profesionales())


def _elegir_profesional(numero: str, texto: str, msg):
    profs = listar_profesionales()
    try:
        idx  = int(texto.strip()) - 1
        prof = profs[idx]
    except (ValueError, IndexError):
        msg.body("❌ Opción inválida.\n\n" + texto_lista_profesionales())
        return

    especialidad = f" — {prof['specialty']}" if prof.get("specialty") else ""
    prof_nombre  = f"{prof['last_name']}, {prof['first_name']}"
    primer_fecha, primer_hora = _primer_turno_disponible(prof["id"])

    set_user_states(numero, {
        "prof_id":               prof["id"],
        "prof_nombre":           prof_nombre,
        "estado":                "TURNO_FECHA",
        "primer_turno_sugerido": f"{primer_fecha}|{primer_hora}" if primer_fecha else None,
    })

    if primer_fecha and primer_hora:
        msg.body(
            f"Turno con *{prof_nombre}*{especialidad}\n\n"
            f"📅 Primer turno disponible:\n"
            f"*{primer_fecha}* a las *{primer_hora} hs*\n\n"
            f"Respondé *S* para confirmar ese horario\n"
            f"o ingresá otra fecha (dd/mm/yyyy):"
        )
    else:
        msg.body(
            f"Turno con *{prof_nombre}*{especialidad}\n\n"
            f"Ingresá la fecha del turno (dd/mm/yyyy):"
        )


def _primer_turno_disponible(prof_id: int) -> tuple:
    """Retorna (fecha_str, hora) del primer slot disponible o (None, None)."""
    from datetime import timedelta
    from config import SEMANAS_AGENDA
    hoy    = datetime.now().date()
    limite = hoy + timedelta(weeks=SEMANAS_AGENDA)
    fecha  = hoy
    while fecha <= limite:
        fecha_str = fecha.strftime("%d/%m/%Y")
        libres    = horarios_libres(prof_id, fecha_str)
        if libres:
            return fecha_str, libres[0]
        fecha += timedelta(days=1)
    return None, None


def _turno_fecha(numero: str, texto: str, msg):
    from datetime import timedelta
    from config import SEMANAS_AGENDA

    # El paciente acepta el primer turno sugerido
    if texto.lower() in ["s", "si", "sí", "yes"]:
        sugerido = get_user_state(numero, "primer_turno_sugerido")
        if sugerido:
            partes = sugerido.split("|")
            if len(partes) == 2:
                fecha_str, hora = partes
                prof_nombre = get_user_state(numero, "prof_nombre")
                set_user_states(numero, {"turno_hora": hora, "estado": "CONFIRMAR_TURNO"})
                set_user_state(numero, "turno_fecha", fecha_str)
                msg.body(
                    f"📋 *Resumen del turno*\n\n"
                    f"👨‍⚕️ {prof_nombre}\n"
                    f"📅 {fecha_str}\n"
                    f"🕐 {hora} hs\n\n"
                    f"¿Confirmás? (S/N)"
                )
                return

    try:
        fecha = datetime.strptime(texto.strip(), "%d/%m/%Y").date()
    except ValueError:
        msg.body("❌ Formato inválido. Usá dd/mm/yyyy (ej: 25/05/2025):")
        return

    hoy    = datetime.now().date()
    limite = hoy + timedelta(weeks=SEMANAS_AGENDA)

    if fecha < hoy:
        msg.body("❌ Esa fecha ya pasó. Ingresá una fecha futura:")
        return

    if fecha > limite:
        msg.body(
            f"❌ Solo podemos tomar turnos hasta el {limite.strftime('%d/%m/%Y')}.\n"
            f"Ingresá una fecha dentro de ese plazo:"
        )
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

    set_user_states(numero, {"turno_fecha": fecha_str, "estado": "TURNO_HORA"})
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
            f"❌ Ese horario está {motivo}. Elegí otro:\n\n" +
            "\n".join(horarios_libres(prof_id, fecha))
        )
        return

    prof_nombre = get_user_state(numero, "prof_nombre")
    set_user_states(numero, {"turno_hora": hora, "estado": "CONFIRMAR_TURNO"})
    msg.body(
        f"📋 *Resumen del turno*\n\n"
        f"👨‍⚕️ {prof_nombre}\n"
        f"📅 {fecha}\n"
        f"🕐 {hora} hs\n\n"
        f"¿Confirmás? (S/N)"
    )


def _confirmar_turno(numero: str, texto: str, msg):
    if texto.lower() in ["s", "si", "sí", "yes"]:
        prof_id     = get_user_state(numero, "prof_id")
        patient_id  = get_user_state(numero, "patient_id")
        fecha       = get_user_state(numero, "turno_fecha")
        hora        = get_user_state(numero, "turno_hora")
        prof_nombre = get_user_state(numero, "prof_nombre")

        agregar_turno(prof_id, patient_id, fecha, hora, created_by="patient")
        msg.body(
            f"✅ *Turno confirmado*\n\n"
            f"👨‍⚕️ {prof_nombre}\n"
            f"📅 {fecha} a las {hora} hs\n\n"
            f"Le enviaremos una confirmación. ¡Hasta el día del turno!"
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
        prof  = f"{t['prof_last_name']}, {t['prof_first_name']}"
        lineas.append(f"📅 {fecha}  🕐 {hora}  👨‍⚕️ {prof}")
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
        prof  = f"{t['prof_last_name']}, {t['prof_first_name']}"
        lineas.append(f"{i+1} — {fecha} {hora} hs  {prof}")

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
# MENSAJE
# ═══════════════════════════════════════════════════════════════════════════════

def _iniciar_mensaje(numero: str, msg):
    paciente = identificar_paciente_por_telefono(numero)
    if paciente:
        set_user_state(numero, "patient_id", paciente["id"])

    # Listar solo profesionales que aceptan mensajes
    profs_con_msj = [p for p in listar_profesionales()
                     if p.get("acepta_mensajes", True)]

    if not profs_con_msj:
        msg.body(
            "ℹ️ Los mensajes no están disponibles en este momento.\n"
            "Para consultas comunicate al consultorio directamente."
        )
        return

    if len(profs_con_msj) == 1:
        set_user_states(numero, {
            "msg_prof_id": profs_con_msj[0]["id"],
            "estado":      "MENSAJE",
        })
        msg.body("Escribí tu mensaje y te respondemos a la brevedad:")
        return

    lineas = [f"{i+1} {p['last_name']}, {p['first_name']}"
              + (f" — {p['specialty']}" if p.get("specialty") else "")
              for i, p in enumerate(profs_con_msj)]

    set_user_states(numero, {
        "profs_msj_ids": [p["id"] for p in profs_con_msj],
        "estado":        "ELEGIR_PROF_MENSAJE",
    })
    msg.body("¿A quién querés enviarle el mensaje?\n\n" + "\n".join(lineas))


def _elegir_prof_mensaje(numero: str, texto: str, msg):
    ids = get_user_state(numero, "profs_msj_ids", [])
    try:
        idx  = int(texto.strip()) - 1
        prof_id = ids[idx]
    except (ValueError, IndexError):
        msg.body("❌ Opción inválida. Elegí un número de la lista:")
        return
    set_user_states(numero, {
        "msg_prof_id": prof_id,
        "estado":      "MENSAJE",
    })
    msg.body("Escribí tu mensaje y te respondemos a la brevedad:")


def _recibir_mensaje(numero: str, texto: str, msg):
    patient_id = get_user_state(numero, "patient_id")
    prof_id    = get_user_state(numero, "msg_prof_id")
    if patient_id:
        guardar_mensaje(patient_id, texto, prof_id)
    msg.body("✅ Mensaje recibido. Te respondemos pronto.")
    set_user_state(numero, "estado", "MENU")

# ═══════════════════════════════════════════════════════════════════════════════
# PROFESIONALES — listado con especialidades (punto 5)
# ═══════════════════════════════════════════════════════════════════════════════

def _ver_profesionales(numero: str, msg):
    profs = listar_profesionales()
    if not profs:
        msg.body("No hay profesionales disponibles en este momento.")
        return

    lineas = [f"👨‍⚕️ *{p['last_name']}, {p['first_name']}*" +
              (f"\n   {p['specialty']}" if p.get('specialty') else "")
              for p in profs]

    msg.body(
        f"🏥 *Profesionales de {NOMBRE_CLINICA}*\n\n" +
        "\n\n".join(lineas) +
        "\n\nEscribí *menu* para volver al inicio."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# INFORMACIÓN — dirección, horarios, Google Maps (punto 6)
# ═══════════════════════════════════════════════════════════════════════════════

def _informacion(numero: str, msg):
    msg.body(
        f"🏥 *{NOMBRE_CLINICA}*\n\n"
        f"📍 {DIRECCION}\n"
        f"📞 {TELEFONO}\n"
        f"🕐 {HORARIO_ATENCION}\n\n"
        f"📌 Cómo llegar:\n{LINK_MAPS}\n\n"
        f"Escribí *menu* para volver al inicio."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SALIR
# ═══════════════════════════════════════════════════════════════════════════════

def _salir(numero: str, msg):
    clear_user(numero)
    msg.body(
        f"¡Hasta luego! 👋\n"
        f"Ante cualquier consulta, escribinos nuevamente.\n"
        f"_{NOMBRE_CLINICA}_"
    )
