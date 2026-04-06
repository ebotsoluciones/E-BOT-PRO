"""
config.py — configuración E-BOT PRO 🦙🔥

Variables de entorno requeridas:
  DATABASE_URL            → Railway PostgreSQL (automática en Railway)
  TWILIO_ACCOUNT_SID      → Credencial Twilio
  TWILIO_AUTH_TOKEN       → Credencial Twilio
  TWILIO_WHATSAPP_FROM    → Número Twilio (ej: whatsapp:+14155238886)

Variables opcionales:
  NOMBRE_CLINICA          → Nombre que aparece en mensajes al paciente
  MODO_TEST               → 'true' para desarrollo local
  STORAGE_BACKEND         → 'postgres' (default) | 'memory' | 'file'
  PORT                    → Puerto Flask (Railway lo setea automático)
"""

import os

# ── Identidad ─────────────────────────────────────────────────────────────────
NOMBRE_CLINICA = os.getenv("NOMBRE_CLINICA", "La Clínica")

# ── Modo ──────────────────────────────────────────────────────────────────────
MODO_TEST = os.getenv("MODO_TEST", "false").lower() == "true"

# ── Twilio ────────────────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID   = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN    = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

# ── Base de datos ─────────────────────────────────────────────────────────────
DATABASE_URL     = os.getenv("DATABASE_URL", "")
STORAGE_BACKEND  = os.getenv("STORAGE_BACKEND", "postgres")

# ── KV store — solo para conversation_state ───────────────────────────────────
# Los datos de negocio (turnos, pacientes, etc.) viven en tablas SQL.
# El KV store queda únicamente para el estado de conversación WhatsApp.
ESTADO_KEY = "conversation_state"

# ── Panel web ─────────────────────────────────────────────────────────────────
# Clave secreta para sesiones Flask del panel web
SECRET_KEY = os.getenv("SECRET_KEY", "cambiar-en-produccion")

# ── Validaciones al startup ───────────────────────────────────────────────────
def validate_config():
    """Avisa en consola si faltan variables críticas."""
    required = {
        "DATABASE_URL":          DATABASE_URL,
        "TWILIO_ACCOUNT_SID":    TWILIO_ACCOUNT_SID,
        "TWILIO_AUTH_TOKEN":     TWILIO_AUTH_TOKEN,
        "TWILIO_WHATSAPP_FROM":  TWILIO_WHATSAPP_FROM,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        print(f"[CONFIG] ⚠️  Variables faltantes: {', '.join(missing)}")
    else:
        print("[CONFIG] ✅ Configuración completa")
    return len(missing) == 0
