"""
notifications.py — envío proactivo WhatsApp E-BOT PRO 🦙🔥

Diferencias respecto a LITE:
  - Los mensajes incluyen el nombre del profesional
  - Notificación va al admin del profesional (no a un número fijo)
  - log_notification() registra cada envío en la tabla notifications
"""

from twilio.rest import Client
from config import (
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN,
    TWILIO_WHATSAPP_FROM, NOMBRE_CLINICA,
)


# ═══════════════════════════════════════════════════════════════════════════════
# CLIENTE TWILIO
# ═══════════════════════════════════════════════════════════════════════════════

def _cliente():
    return Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def _enviar(para: str, mensaje: str):
    """Envía un mensaje WhatsApp. Silencia errores para no romper el flujo."""
    if not para:
        return
    try:
        _cliente().messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            to=para,
            body=mensaje,
        )
    except Exception as e:
        print(f"[NOTIF ERROR] {e}")

def _firma(prof_nombre: str = None) -> str:
    if prof_nombre:
        return f"{NOMBRE_CLINICA} — {prof_nombre}"
    return NOMBRE_CLINICA


# ═══════════════════════════════════════════════════════════════════════════════
# PACIENTE
# ═══════════════════════════════════════════════════════════════════════════════

def notif_paciente_confirmado(telefono: str, nombre: str, fecha: str,
                               hora: str, prof_nombre: str = None):
    prof_linea = f"👨‍⚕️ {prof_nombre}\n" if prof_nombre else ""
    msg = (
        f"✅ *Turno confirmado*\n"
        f"Hola {nombre.split()[0]}, tu turno quedó registrado.\n\n"
        f"{prof_linea}"
        f"📅 {fecha} a las {hora} hs\n\n"
        f"Ante cualquier consulta respondé este mensaje.\n"
        f"_{_firma(prof_nombre)}_"
    )
    _enviar(telefono, msg)

def notif_paciente_cancelado(telefono: str, nombre: str, fecha: str,
                              hora: str, prof_nombre: str = None):
    prof_linea = f"👨‍⚕️ {prof_nombre}\n" if prof_nombre else ""
    msg = (
        f"❌ *Turno cancelado*\n"
        f"Hola {nombre.split()[0]}, tu turno fue cancelado.\n\n"
        f"{prof_linea}"
        f"📅 {fecha} a las {hora} hs\n\n"
        f"Podés sacar un nuevo turno cuando quieras.\n"
        f"_{_firma(prof_nombre)}_"
    )
    _enviar(telefono, msg)

def notif_paciente_recordatorio(telefono: str, nombre: str, fecha: str,
                                 hora: str, prof_nombre: str = None):
    """Recordatorio 24hs antes del turno (llamar desde un scheduler)."""
    prof_linea = f"👨‍⚕️ {prof_nombre}\n" if prof_nombre else ""
    msg = (
        f"🔔 *Recordatorio de turno*\n"
        f"Hola {nombre.split()[0]}, te recordamos tu turno de mañana.\n\n"
        f"{prof_linea}"
        f"📅 {fecha} a las {hora} hs\n\n"
        f"_{_firma(prof_nombre)}_"
    )
    _enviar(telefono, msg)


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN / PROFESIONAL
# ═══════════════════════════════════════════════════════════════════════════════

def notif_admin_nuevo_turno(nombre: str, telefono: str,
                             fecha: str, hora: str, dest_phone: str = None):
    """Notifica al profesional (o admin) que se sacó un nuevo turno."""
    if not dest_phone:
        return
    msg = (
        f"🔔 *Nuevo turno*\n"
        f"👤 {nombre}\n"
        f"📱 {telefono.replace('whatsapp:+', '+')}\n"
        f"📅 {fecha} a las {hora} hs"
    )
    _enviar(dest_phone, msg)

def notif_admin_cancelado(nombre: str, telefono: str,
                           fecha: str, hora: str, dest_phone: str = None):
    """Notifica al profesional (o admin) que se canceló un turno."""
    if not dest_phone:
        return
    msg = (
        f"🗑 *Turno cancelado*\n"
        f"👤 {nombre}\n"
        f"📱 {telefono.replace('whatsapp:+', '+')}\n"
        f"📅 {fecha} a las {hora} hs"
    )
    _enviar(dest_phone, msg)


# ═══════════════════════════════════════════════════════════════════════════════
# BROADCAST (uso futuro — campañas / recordatorios masivos)
# ═══════════════════════════════════════════════════════════════════════════════

def notif_broadcast(telefonos: list[str], mensaje: str):
    """Envía el mismo mensaje a una lista de números."""
    for tel in telefonos:
        _enviar(tel, mensaje)
