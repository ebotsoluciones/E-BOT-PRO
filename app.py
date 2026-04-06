"""
app.py — servidor Flask E-BOT PRO 🦙🔥
"Llama que llama... por wasap"
"""

import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

from config   import SECRET_KEY, validate_config
from db       import init_db
from handlers import procesar

app = Flask(__name__)
app.secret_key = SECRET_KEY

# ── Startup ───────────────────────────────────────────────────────────────────
validate_config()
init_db()


# ═══════════════════════════════════════════════════════════════════════════════
# RUTAS WHATSAPP
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/", methods=["GET"])
def health():
    return "🦙 E-BOT PRO — OK", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    numero = request.form.get("From", "")
    body   = request.form.get("Body", "").strip()
    resp   = MessagingResponse()
    procesar(numero, body, resp)
    return str(resp), 200, {"Content-Type": "text/xml"}


# ═══════════════════════════════════════════════════════════════════════════════
# RUTAS PANEL WEB (Fase 6 — placeholder)
# ═══════════════════════════════════════════════════════════════════════════════

# from web.routes import web_bp
# app.register_blueprint(web_bp, url_prefix="/admin")


# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
