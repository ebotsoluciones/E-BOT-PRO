"""
web/routes.py — rutas del panel web E-BOT PRO 🦙🔥

Rutas:
  GET  /admin/              → login
  POST /admin/login         → autenticar
  GET  /admin/dashboard     → vista principal
  GET  /admin/agenda        → agenda por profesional y fecha
  GET  /admin/pacientes     → listado de pacientes
  GET  /admin/mensajes      → mensajes pendientes
  GET  /admin/reportes      → reportes mensuales
  POST /admin/turno/nuevo   → crear turno manual
  POST /admin/turno/cancelar → cancelar turno
  POST /admin/bloqueo/nuevo → bloquear horario
  POST /admin/logout        → cerrar sesión
"""

from datetime import datetime, date
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, flash, jsonify,
)
from db import (
    get_professionals, get_professional_by_id,
    get_appointments_by_date, get_upcoming_appointments,
    get_pending_messages, mark_all_read,
    get_report_by_month, get_patient_by_id,
)
from services import (
    listar_profesionales, horarios_libres,
    agregar_turno, cancelar_turno_por_slot,
    bloquear_horario, bloquear_dia_completo,
    texto_reporte,
)

web_bp = Blueprint("web", __name__, template_folder="templates")

# ── Clave de acceso simple (en producción usar DB de admins) ──────────────────
ADMIN_PASSWORD = "ebot2025"  # TODO: mover a variable de entorno WEB_PASSWORD


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════════════════════════

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged"):
            return redirect(url_for("web.login"))
        return f(*args, **kwargs)
    return decorated


@web_bp.route("/")
def login():
    if session.get("admin_logged"):
        return redirect(url_for("web.dashboard"))
    return render_template("login.html")


@web_bp.route("/login", methods=["POST"])
def do_login():
    password = request.form.get("password", "")
    if password == ADMIN_PASSWORD:
        session["admin_logged"] = True
        return redirect(url_for("web.dashboard"))
    flash("Contraseña incorrecta")
    return redirect(url_for("web.login"))


@web_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("web.login"))


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

@web_bp.route("/dashboard")
@login_required
def dashboard():
    hoy       = date.today()
    profs     = listar_profesionales()
    mensajes  = get_pending_messages()
    reporte   = get_report_by_month(hoy.year, hoy.month)

    # Turnos de hoy por profesional
    turnos_hoy = []
    for p in profs:
        lista = get_appointments_by_date(p["id"], hoy.isoformat())
        turnos_hoy.append({
            "profesional": p,
            "turnos":      lista,
            "total":       len(lista),
        })

    return render_template("dashboard.html",
        profs=profs,
        turnos_hoy=turnos_hoy,
        mensajes_pendientes=len(mensajes),
        reporte=reporte["summary"],
        hoy=hoy.strftime("%d/%m/%Y"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# AGENDA
# ═══════════════════════════════════════════════════════════════════════════════

@web_bp.route("/agenda")
@login_required
def agenda():
    from datetime import timedelta
    DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

    profs     = listar_profesionales()
    prof_id   = request.args.get("prof_id", type=int)
    fecha_str = request.args.get("fecha", date.today().strftime("%d/%m/%Y"))

    try:
        fecha_sel = datetime.strptime(fecha_str, "%d/%m/%Y").date()
    except ValueError:
        fecha_sel = date.today()
        fecha_str = fecha_sel.strftime("%d/%m/%Y")

    # Calcular semana (lunes a domingo)
    lunes = fecha_sel - timedelta(days=fecha_sel.weekday())
    dias_semana = []
    for i in range(7):
        d = lunes + timedelta(days=i)
        dias_semana.append({
            "nombre":    DIAS[i],
            "numero":    d.strftime("%d"),
            "fecha_str": d.strftime("%d/%m/%Y"),
        })

    turnos   = []
    horarios = []
    prof_sel = None

    if prof_id:
        fecha_iso = fecha_sel.isoformat()
        prof_sel  = get_professional_by_id(prof_id)
        turnos    = get_appointments_by_date(prof_id, fecha_iso)
        horarios  = horarios_libres(prof_id, fecha_str)

    semana_anterior = (lunes - timedelta(days=7)).strftime("%d/%m/%Y")
    semana_siguiente = (lunes + timedelta(days=7)).strftime("%d/%m/%Y")

    return render_template("agenda.html",
        profs=profs,
        prof_sel=prof_sel,
        prof_id=prof_id,
        fecha=fecha_str,
        turnos=turnos,
        horarios=horarios,
        dias_semana=dias_semana,
        semana_inicio=lunes.strftime("%d/%m/%Y"),
        semana_fin=(lunes + timedelta(days=6)).strftime("%d/%m/%Y"),
        semana_anterior=semana_anterior,
        semana_siguiente=semana_siguiente,
        hoy=date.today().strftime("%d/%m/%Y"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# MENSAJES
# ═══════════════════════════════════════════════════════════════════════════════

@web_bp.route("/mensajes")
@login_required
def mensajes():
    from db import get_all_patients
    prof_id    = request.args.get("prof_id", type=int)
    paciente_q = request.args.get("paciente", "").strip()
    profs      = listar_profesionales()
    mensajes   = get_pending_messages(prof_id)

    # Filtrar por paciente si se ingresó búsqueda
    if paciente_q:
        q = paciente_q.lower()
        mensajes = [m for m in mensajes
                    if q in (m.get("patient_name") or "").lower()
                    or q in (m.get("patient_phone") or "").lower()]

    return render_template("mensajes.html",
        mensajes=mensajes,
        profs=profs,
        prof_id=prof_id,
        paciente_q=paciente_q,
    )


@web_bp.route("/mensajes/leer", methods=["POST"])
@login_required
def marcar_leido():
    prof_id = request.form.get("prof_id", type=int)
    mark_all_read(prof_id)
    flash("✅ Mensajes marcados como leídos.")
    return redirect(url_for("web.mensajes", prof_id=prof_id))


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTES
# ═══════════════════════════════════════════════════════════════════════════════

@web_bp.route("/reportes")
@login_required
def reportes():
    from db import get_report_by_range
    hoy     = date.today()
    prof_id = request.args.get("prof_id", type=int)
    modo    = request.args.get("modo", "")
    profs   = listar_profesionales()

    if modo == "todo":
        desde = "2024-01-01"
        hasta = hoy.isoformat()
    else:
        desde = request.args.get("desde", date(hoy.year, hoy.month, 1).isoformat())
        hasta = request.args.get("hasta", hoy.isoformat())

    reporte = get_report_by_range(desde, hasta, prof_id)

    return render_template("reportes.html",
        profs=profs,
        prof_id=prof_id,
        desde=desde,
        hasta=hasta,
        reporte=reporte,
    )


@web_bp.route("/reportes/borrar", methods=["POST"])
@login_required
def borrar_historico():
    from db import borrar_turnos_anteriores
    hasta_fecha = request.form.get("hasta_fecha")
    prof_id     = request.form.get("prof_id", type=int)
    if hasta_fecha:
        borrar_turnos_anteriores(hasta_fecha, prof_id)
        flash(f"✅ Turnos anteriores al {hasta_fecha} eliminados correctamente.")
    else:
        flash("❌ Fecha inválida.")
    return redirect(url_for("web.reportes", prof_id=prof_id))


# ═══════════════════════════════════════════════════════════════════════════════
# TURNO — nuevo y cancelar (API JSON para el panel)
# ═══════════════════════════════════════════════════════════════════════════════

@web_bp.route("/turno/nuevo", methods=["POST"])
@login_required
def nuevo_turno():
    prof_id    = request.form.get("prof_id",    type=int)
    patient_id = request.form.get("patient_id", type=int)
    fecha      = request.form.get("fecha")
    hora       = request.form.get("hora")

    if not all([prof_id, patient_id, fecha, hora]):
        flash("❌ Faltan datos para crear el turno.")
        return redirect(url_for("web.agenda", prof_id=prof_id, fecha=fecha))

    try:
        agregar_turno(prof_id, patient_id, fecha, hora, created_by="web_admin")
        flash(f"✅ Turno creado: {fecha} {hora} hs")
    except Exception as e:
        flash(f"❌ Error al crear turno: {e}")

    return redirect(url_for("web.agenda", prof_id=prof_id, fecha=fecha))


@web_bp.route("/turno/cancelar", methods=["POST"])
@login_required
def cancelar_turno_web():
    prof_id = request.form.get("prof_id", type=int)
    fecha   = request.form.get("fecha")
    hora    = request.form.get("hora")

    turno = cancelar_turno_por_slot(prof_id, fecha, hora, cancelled_by="web_admin")
    if turno:
        flash(f"✅ Turno cancelado: {turno['patient_name']} — {fecha} {hora} hs")
    else:
        flash("❌ No se encontró el turno.")

    return redirect(url_for("web.agenda", prof_id=prof_id, fecha=fecha))


# ═══════════════════════════════════════════════════════════════════════════════
# BLOQUEO
# ═══════════════════════════════════════════════════════════════════════════════

@web_bp.route("/bloqueo/nuevo", methods=["POST"])
@login_required
def nuevo_bloqueo():
    prof_id = request.form.get("prof_id", type=int)
    fecha   = request.form.get("fecha")
    hora    = request.form.get("hora")
    todos   = request.form.get("todos") == "1"

    if todos:
        bloquear_dia_completo(prof_id, fecha, created_by="web_admin")
        flash(f"✅ Día {fecha} bloqueado completo.")
    else:
        bloquear_horario(prof_id, fecha, hora, created_by="web_admin")
        flash(f"✅ Horario bloqueado: {fecha} {hora} hs")

    return redirect(url_for("web.agenda", prof_id=prof_id, fecha=fecha))


# ═══════════════════════════════════════════════════════════════════════════════
# API JSON — horarios libres (para selector dinámico en el panel)
# ═══════════════════════════════════════════════════════════════════════════════

@web_bp.route("/api/horarios")
@login_required
def api_horarios():
    prof_id = request.args.get("prof_id", type=int)
    fecha   = request.args.get("fecha")
    if not prof_id or not fecha:
        return jsonify([])
    return jsonify(horarios_libres(prof_id, fecha))


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _nombres_meses():
    return [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# PROFESIONALES — ABM
# ═══════════════════════════════════════════════════════════════════════════════

@web_bp.route("/profesionales")
@login_required
def profesionales():
    from db import get_professionals
    profs = get_professionals(active_only=False)
    return render_template("profesionales.html", profs=profs)


@web_bp.route("/profesionales/nuevo", methods=["POST"])
@login_required
def crear_profesional():
    from db import create_professional
    last_name  = request.form.get("last_name", "").strip()
    first_name = request.form.get("first_name", "").strip()
    specialty  = request.form.get("specialty", "").strip() or None
    phone      = request.form.get("phone", "").strip() or None
    if last_name and first_name:
        create_professional(last_name, first_name, specialty, phone)
        flash(f"✅ Profesional {last_name}, {first_name} creado correctamente.")
    else:
        flash("❌ Apellido y nombre son obligatorios.")
    return redirect(url_for("web.profesionales"))


@web_bp.route("/profesionales/editar", methods=["POST"])
@login_required
def editar_profesional():
    from db import update_professional
    prof_id    = request.form.get("prof_id", type=int)
    last_name  = request.form.get("last_name", "").strip()
    first_name = request.form.get("first_name", "").strip()
    specialty  = request.form.get("specialty", "").strip() or None
    phone      = request.form.get("phone", "").strip() or None
    if prof_id and last_name and first_name:
        update_professional(prof_id, last_name, first_name, specialty, phone)
        flash("✅ Profesional actualizado.")
    else:
        flash("❌ Datos incompletos.")
    return redirect(url_for("web.profesionales"))


@web_bp.route("/profesionales/<int:prof_id>/baja", methods=["POST"])
@login_required
def desactivar_profesional(prof_id):
    from db import deactivate_professional
    deactivate_professional(prof_id)
    flash("✅ Profesional dado de baja.")
    return redirect(url_for("web.profesionales"))


@web_bp.route("/profesionales/horarios", methods=["POST"])
@login_required
def guardar_horarios():
    from db import upsert_schedule, delete_schedule
    prof_id = request.form.get("prof_id", type=int)
    if not prof_id:
        flash("❌ Profesional no encontrado.")
        return redirect(url_for("web.profesionales"))

    delete_schedule(prof_id)

    dias_nombres = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
    for i in range(7):
        if request.form.get(f"active_{i}"):
            start = request.form.get(f"start_{i}", "09:00")
            end   = request.form.get(f"end_{i}",   "18:00")
            slot  = int(request.form.get(f"slot_{i}", 30))
            upsert_schedule(prof_id, i, start, end, slot)

    flash("✅ Horarios guardados correctamente.")
    return redirect(url_for("web.profesionales"))


# ═══════════════════════════════════════════════════════════════════════════════
# API — PACIENTES (búsqueda y alta rápida desde agenda)
# ═══════════════════════════════════════════════════════════════════════════════

@web_bp.route("/api/paciente")
@login_required
def api_buscar_paciente():
    from db import get_patient_by_dni, get_all_patients
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"found": False})

    # Buscar por DNI
    if q.isdigit():
        p = get_patient_by_dni(q)
        if p:
            return jsonify({
                "found": True, "id": p["id"], "name": p["name"],
                "dni": p["dni"], "obra_social": p.get("obra_social")
            })
    else:
        # Buscar por apellido/nombre (búsqueda parcial)
        todos = get_all_patients()
        q_lower = q.lower()
        coincidencias = [p for p in todos if q_lower in p["name"].lower()]
        if coincidencias:
            p = coincidencias[0]
            return jsonify({
                "found": True, "id": p["id"], "name": p["name"],
                "dni": p["dni"], "obra_social": p.get("obra_social")
            })

    return jsonify({"found": False})


@web_bp.route("/api/paciente/alta", methods=["POST"])
@login_required
def api_alta_paciente():
    from db import create_patient, get_patient_by_dni
    import json as _json
    data = request.get_json()
    nombre     = (data.get("nombre") or "").strip()
    dni        = (data.get("dni")    or "").strip().replace(".", "")
    obra_social = data.get("obra_social")

    if not nombre or not dni:
        return jsonify({"ok": False, "error": "Nombre y DNI son obligatorios."})

    # Verificar que no exista
    existente = get_patient_by_dni(dni)
    if existente:
        return jsonify({
            "ok": True, "id": existente["id"],
            "name": existente["name"], "dni": existente["dni"]
        })

    try:
        p = create_patient("", nombre, dni, obra_social)
        return jsonify({"ok": True, "id": p["id"], "name": p["name"], "dni": p["dni"]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


# ═══════════════════════════════════════════════════════════════════════════════
# PROFESIONALES — vincular WhatsApp (alta en tabla admins)
# ═══════════════════════════════════════════════════════════════════════════════

@web_bp.route("/profesionales/<int:prof_id>/whatsapp", methods=["POST"])
@login_required
def vincular_whatsapp_prof(prof_id):
    from db import create_admin, get_admin_by_phone, get_professional_by_id
    phone = request.form.get("phone", "").strip()
    if not phone:
        flash("❌ Ingresá un número de WhatsApp.")
        return redirect(url_for("web.profesionales"))

    # Normalizar formato
    if not phone.startswith("whatsapp:"):
        phone = "whatsapp:" + phone

    prof = get_professional_by_id(prof_id)
    if not prof:
        flash("❌ Profesional no encontrado.")
        return redirect(url_for("web.profesionales"))

    # Verificar si ya existe
    existente = get_admin_by_phone(phone)
    if existente:
        flash(f"⚠️ Ese número ya está registrado como admin.")
        return redirect(url_for("web.profesionales"))

    nombre = f"{prof['last_name']}, {prof['first_name']}"
    create_admin(phone, nombre, role="professional", professional_id=prof_id)
    flash(f"✅ WhatsApp vinculado a {nombre}.")
    return redirect(url_for("web.profesionales"))


# ═══════════════════════════════════════════════════════════════════════════════
# PROFESIONALES — toggle mensajes
# ═══════════════════════════════════════════════════════════════════════════════

@web_bp.route("/profesionales/<int:prof_id>/mensajes", methods=["POST"])
@login_required
def toggle_mensajes_prof(prof_id):
    from db import toggle_mensajes, get_professional_by_id
    prof  = get_professional_by_id(prof_id)
    nuevo = not prof.get("acepta_mensajes", True)
    toggle_mensajes(prof_id, nuevo)
    estado = "activados" if nuevo else "desactivados"
    flash(f"✅ Mensajes {estado} para {prof['last_name']}, {prof['first_name']}.")
    return redirect(url_for("web.profesionales"))

