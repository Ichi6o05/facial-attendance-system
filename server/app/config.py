"""
config.py - Configuración centralizada del servidor
Carga variables de entorno y define constantes del sistema
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Rutas base
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PHOTOS_DIR = DATA_DIR / "photos" / "student_photos"
LOGS_DIR = DATA_DIR / "logs"

# Crear directorios si no existen
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ====================================
# CONFIGURACIÓN DE BASE DE DATOS
# ====================================

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
    "database": os.getenv("DB_NAME"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "charset": "utf8mb4",
    "collation": "utf8mb4_unicode_ci",
}

# ====================================
# CONFIGURACIÓN DEL SERVIDOR
# ====================================

SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", 8000))

# Seguridad
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY no configurada en .env")

# CORS - Orígenes permitidos
ALLOWED_ORIGINS_STR = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_STR.split(",")]

# ====================================
# RECONOCIMIENTO FACIAL
# ====================================

# Tolerancia de reconocimiento (0.0-1.0)
# Valores más bajos = más estricto
# Recomendado: 0.6
FACE_TOLERANCE = float(os.getenv("FACE_TOLERANCE", 0.6))

# Modelo de detección de rostros
# "hog" = Rápido, CPU-friendly (recomendado)
# "cnn" = Más preciso, requiere GPU
FACE_DETECTION_MODEL = os.getenv("FACE_DETECTION_MODEL", "hog")

# Archivo de encodings (cache)
ENCODINGS_FILE = DATA_DIR / "photos" / "encodings.pkl"

# Retención de fotos después de generar encodings
# IMPORTANTE: Consideraciones legales (Ley 19.628 Chile):
# - Fotos = datos biométricos sensibles que requieren consentimiento explícito
# - Principio de minimización: solo guardar datos estrictamente necesarios
# - Encodings (128D vectors) son suficientes para reconocimiento
# - Eliminar fotos reduce riesgo en caso de breach (no se pueden revertir encodings)
#
# true  = Mantener fotos (útil para debugging, requiere consentimiento explícito)
# false = Eliminar fotos después de encoding (recomendado para cumplimiento legal)
KEEP_PHOTOS_AFTER_ENCODING = os.getenv("KEEP_PHOTOS_AFTER_ENCODING", "false").lower() == "true"

# ====================================
# SISTEMA DE ASISTENCIA
# ====================================

# Cooldown entre registros del mismo estudiante (segundos)
# Evita registros duplicados por error
COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS", 300))  # 5 minutos

# Tamaño máximo de archivo de foto (MB)
MAX_PHOTO_SIZE_MB = 10
MAX_PHOTO_SIZE_BYTES = MAX_PHOTO_SIZE_MB * 1024 * 1024

# Formatos de imagen permitidos
ALLOWED_IMAGE_FORMATS = ["image/jpeg", "image/png"]

# ====================================
# PROCESAMIENTO DE IMÁGENES
# ====================================

# Redimensionar frames para procesamiento más rápido
FRAME_RESIZE_WIDTH = 480

# ====================================
# WEBSOCKETS
# ====================================

# Timeout para conexiones WebSocket (segundos)
WS_TIMEOUT = 60

# Intervalo de ping/pong para mantener conexión viva (segundos)
WS_PING_INTERVAL = 30

# Máximo de viewers simultáneos por dispositivo (streaming)
MAX_VIEWERS_PER_DEVICE = int(os.getenv("MAX_VIEWERS_PER_DEVICE", 5))

# ====================================
# LOGGING
# ====================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = LOGS_DIR / "server.log"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ====================================
# RATE LIMITING
# ====================================

# Límite de requests por minuto para endpoints de procesamiento
# Cada Raspberry envía cada 2 seg = 30 req/min
# Con 2 Raspberries = 60 req/min
RATE_LIMIT_PROCESS_FRAME = "100/minute"

# Límite de requests por minuto para endpoints de lectura
RATE_LIMIT_READ = "60/minute"

# Límite de requests por minuto para endpoints de escritura
RATE_LIMIT_WRITE = "30/minute"

# ====================================
# VALIDACIÓN
# ====================================

# Expresión regular para RUT chileno
RUT_REGEX = r"^\d{1,2}\.\d{3}\.\d{3}-[\dkK]$"

# Longitud mínima/máxima para nombres
MIN_NAME_LENGTH = 3
MAX_NAME_LENGTH = 100

# ====================================
# PERFORMANCE
# ====================================

# Número de workers para procesamiento asíncrono
ASYNC_WORKERS = 4

# ====================================
# INFORMACIÓN DEL SISTEMA
# ====================================

APP_NAME = "Sistema de Asistencia IoT"
APP_VERSION = "2.0.0"
APP_DESCRIPTION = "API para reconocimiento facial y registro de asistencia"

# ====================================
# VALIDACIÓN DE CONFIGURACIÓN
# ====================================

def validate_config():
    """
    Valida que toda la configuración necesaria esté presente
    """
    required_vars = {
        "DB_USER": DB_CONFIG["user"],
        "DB_PASS": DB_CONFIG["password"],
        "DB_NAME": DB_CONFIG["database"],
        "SECRET_KEY": SECRET_KEY,
    }

    missing_vars = [key for key, value in required_vars.items() if not value]

    if missing_vars:
        raise ValueError(
            f"Faltan las siguientes variables de entorno: {', '.join(missing_vars)}\n"
            f"Por favor, configura el archivo .env basándote en .env.example"
        )

    # Validar tolerancia de reconocimiento facial
    if not 0.0 <= FACE_TOLERANCE <= 1.0:
        raise ValueError("FACE_TOLERANCE debe estar entre 0.0 y 1.0")

    # Validar modelo de detección
    if FACE_DETECTION_MODEL not in ["hog", "cnn"]:
        raise ValueError("FACE_DETECTION_MODEL debe ser 'hog' o 'cnn'")

    print("✅ Configuración validada correctamente")

# Ejecutar validación al importar
if __name__ != "__main__":
    try:
        validate_config()
    except ValueError as e:
        print(f"❌ Error de configuración: {e}")
        raise
