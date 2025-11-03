"""
config.py - Configuración Raspberry Pi Client
"""

import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# ====================================
# CONFIGURACIÓN DEL SERVIDOR
# ====================================

SERVER_HOST = os.getenv("SERVER_HOST")
SERVER_PROTOCOL = os.getenv("SERVER_PROTOCOL", "https")
SERVER_URL = f"{SERVER_PROTOCOL}://{SERVER_HOST}"
WS_URL = f"wss://{SERVER_HOST}/ws" if SERVER_PROTOCOL == "https" else f"ws://{SERVER_HOST}/ws"

# ====================================
# IDENTIFICACIÓN DEL DISPOSITIVO
# ====================================

DEVICE_ID = os.getenv("DEVICE_ID", "pi-aula-101")

# ====================================
# CONFIGURACIÓN DE CÁMARA
# ====================================

FRAME_WIDTH = int(os.getenv("FRAME_WIDTH", 640))
FRAME_HEIGHT = int(os.getenv("FRAME_HEIGHT", 480))
CAPTURE_INTERVAL = float(os.getenv("CAPTURE_INTERVAL", 1.0))

# ====================================
# CONFIGURACIÓN GPIO
# ====================================

LED_GREEN_PIN = int(os.getenv("LED_GREEN_PIN", 17))
LED_RED_PIN = int(os.getenv("LED_RED_PIN", 27))
LED_DURATION = int(os.getenv("LED_DURATION", 2))

# ====================================
# CONFIGURACIÓN DE CONEXIÓN
# ====================================

REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 5))
WS_RECONNECT_DELAY = int(os.getenv("WS_RECONNECT_DELAY", 5))

# ====================================
# STREAM DE VIDEO (MONITOREO)
# ====================================

ENABLE_WEB_STREAM = os.getenv("ENABLE_WEB_STREAM", "true").lower() == "true"
WEB_STREAM_PORT = int(os.getenv("WEB_STREAM_PORT", 8080))

# WebSocket streaming para frontend centralizado
ENABLE_WS_STREAMING = os.getenv("ENABLE_WS_STREAMING", "true").lower() == "true"
WS_STREAM_FPS = float(os.getenv("WS_STREAM_FPS", 0.5))  # Frames por segundo para WebSocket

# ====================================
# VALIDACIÓN
# ====================================

def validate_config():
    """Valida la configuración antes de iniciar"""
    errors = []

    if not SERVER_HOST:
        errors.append("SERVER_HOST no configurado")

    if not DEVICE_ID:
        errors.append("DEVICE_ID no configurado")

    if FRAME_WIDTH <= 0 or FRAME_HEIGHT <= 0:
        errors.append("FRAME_WIDTH y FRAME_HEIGHT deben ser mayores a 0")

    if not (1 <= LED_GREEN_PIN <= 27) or not (1 <= LED_RED_PIN <= 27):
        errors.append("Pines GPIO deben estar entre 1 y 27")

    if errors:
        raise ValueError("Errores de configuración:\n- " + "\n- ".join(errors))

    print("✅ Configuración de Raspberry Pi validada")

# Validar al importar
if __name__ != "__main__":
    try:
        validate_config()
    except ValueError as e:
        print(f"❌ Error de configuración: {e}")
        raise
