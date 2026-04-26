"""
handlers.py — router principal E-BOT PRO 🦙🔥

Responsabilidad única: decidir si el mensaje viene de un admin
o de un paciente y derivarlo al handler correcto.
"""

from db      import get_admin_by_phone
from storage import get_user_state, set_user_state, clear_user
from config  import MODO_TEST

from handlers_paciente import manejar_paciente, menu_paciente
from handlers_admin    import manejar_admin, MENU_ADMIN_PROF, MENU_ADMIN_GENERAL


# Estados que pertenecen al flujo admin
_ESTADOS_ADMIN = {
    "ADMIN", "ADMIN_ELEGIR_PROF",
    "ADMIN_NUEVO_NOMBRE", "ADMIN_NUEVO_DNI",
    "ADMIN_NUEVO_FECHA",  "ADMIN_NUEVO_HORA",
    "ADMIN_CANCEL_FECHA", "ADMIN_CANCEL_HORA",
    "BLOQUEAR_FECHA",     "BLOQUEAR_HORA",
}


def procesar(numero: str, body: str, resp):
    texto  = body.strip()
    msg    = resp.message()
    estado = get_user_state(numero, "estado", "MENU")

    # ── Reset global — siempre disponible ────────────────────────────────────
    if texto.lower() in ["menu", "/start", "inicio"]:
        clear_user(numero)
        # Si es admin, mostrar su menú; si no, el del paciente
        admin = get_admin_by_phone(numero)
        if admin:
            set_user_state(numero, "estado", "ADMIN")
            es_general = admin["role"] == "general"
            msg.body(MENU_ADMIN_GENERAL if es_general else MENU_ADMIN_PROF)
        else:
            msg.body(menu_paciente())
        return

    # ── Modo test: activar admin con "adm" ───────────────────────────────────
    if MODO_TEST and texto.lower() == "adm":
        set_user_state(numero, "estado", "ADMIN")
        msg.body(MENU_ADMIN_GENERAL)
        return

    # ── Marcar mensajes como leídos ──────────────────────────────────────────
    if texto.lower() == "3r" and estado in _ESTADOS_ADMIN:
        from services import marcar_mensajes_leidos
        admin = get_admin_by_phone(numero)
        prof_id = admin.get("professional_id") if admin else None
        marcar_mensajes_leidos(prof_id)
        msg.body("✅ Mensajes marcados como leídos.")
        return

    # ── Detectar admin al primer mensaje ─────────────────────────────────────
    # Si el estado es MENU y el número es admin, derivar automáticamente
    if estado == "MENU" and not MODO_TEST:
        admin = get_admin_by_phone(numero)
        if admin and admin["role"] in ("general", "professional"):
            set_user_state(numero, "estado", "ADMIN")
            es_general = admin["role"] == "general"
            msg.body(MENU_ADMIN_GENERAL if es_general else MENU_ADMIN_PROF)
            return

    # ── Router principal ──────────────────────────────────────────────────────
    if estado in _ESTADOS_ADMIN:
        manejar_admin(numero, body, msg)
    else:
        manejar_paciente(numero, body, msg)

    
