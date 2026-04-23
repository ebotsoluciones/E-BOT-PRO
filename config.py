"""
config.py — configuración E-BOT PRO 🦙🔥
"""

import os

# ── Identidad ─────────────────────────────────────────────────────────────────
NOMBRE_CLINICA     = os.getenv("NOMBRE_CLINICA",    "Centro Médico Zumarán")
DIRECCION          = os.getenv("DIRECCION",          "Av. Monseñor Pablo Cabrera 3200, Córdoba")
TELEFONO           = os.getenv("TELEFONO",           "0351 476-7176")
HORARIO_ATENCION   = os.getenv("HORARIO_ATENCION",   "Lunes a jueves de 8:00 a 21:00 hs")
LINK_MAPS          = os.getenv("LINK_MAPS",          "https://maps.app.goo.gl/qTGkD5YfwmPFtPrR6")
TELEFONO_URGENCIAS = os.getenv("TELEFONO_URGENCIAS", "0351 476-7176")

# ── Agenda ────────────────────────────────────────────────────────────────────
# Cuántas semanas hacia adelante puede sacar turno el paciente
# Ejemplos: 4 = 1 mes, 8 = 2 meses, 17 = 4 meses (útil para PAMI)
SEMANAS_AGENDA = int(os.getenv("SEMANAS_AGENDA", "8"))

# ── Modo ──────────────────────────────────────────────────────────────────────
MODO_TEST = os.getenv("MODO_TEST", "false").lower() == "true"

# ── Twilio ────────────────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID   = os.getenv("TWILIO_ACCOUNT_SID",   "")
TWILIO_AUTH_TOKEN    = os.getenv("TWILIO_AUTH_TOKEN",     "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM",  "whatsapp:+14155238886")

# ── Base de datos ─────────────────────────────────────────────────────────────
DATABASE_URL    = os.getenv("DATABASE_URL",    "")
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "postgres")

# ── KV store ──────────────────────────────────────────────────────────────────
ESTADO_KEY = "conversation_state"

# ── Panel web ─────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "cambiar-en-produccion")

# ── Validaciones al startup ───────────────────────────────────────────────────
def validate_config():
    required = {
        "DATABASE_URL":         DATABASE_URL,
        "TWILIO_ACCOUNT_SID":   TWILIO_ACCOUNT_SID,
        "TWILIO_AUTH_TOKEN":    TWILIO_AUTH_TOKEN,
        "TWILIO_WHATSAPP_FROM": TWILIO_WHATSAPP_FROM,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        print(f"[CONFIG] ⚠️  Variables faltantes: {', '.join(missing)}")
    else:
        print("[CONFIG] ✅ Configuración completa")
    return len(missing) == 0
