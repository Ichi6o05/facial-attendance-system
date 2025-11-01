"""
main.py - API principal FastAPI del servidor
Recibe frames, procesa reconocimiento facial y gestiona asistencia
"""

# ====================================
# IMPORTACIONES
# ====================================

import logging
import uvicorn
import os
import re
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional, List

from fastapi import FastAPI, HTTPException, Request, File, UploadFile, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import (
    SERVER_HOST,
    SERVER_PORT,
    ALLOWED_ORIGINS,
    COOLDOWN_SECONDS,
    PHOTOS_DIR,
    RATE_LIMIT_PROCESS_FRAME,
    RATE_LIMIT_READ,
    RATE_LIMIT_WRITE,
    ASYNC_WORKERS,
    APP_NAME,
    APP_VERSION,
    APP_DESCRIPTION,
    LOG_LEVEL,
    LOG_FORMAT,
    MAX_VIEWERS_PER_DEVICE
)
from app.core.database import db
from app.core.face_recognition import face_recognition_processor

# ====================================
# CONFIGURACIÓN DE LOGGING
# ====================================

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT
)
logger = logging.getLogger(__name__)

# ====================================
# EVENTOS DE CICLO DE VIDA
# ====================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Contexto de ciclo de vida de la aplicación
    Reemplaza los deprecated on_event("startup") y on_event("shutdown")
    """
    # STARTUP
    logger.info(f"Iniciando {APP_NAME} v{APP_VERSION}...")

    # Verificar si hay encodings cargados
    if not face_recognition_processor.encodings_loaded:
        logger.warning("Encodings no cargados. Generando desde fotos...")
        estudiantes = db.obtener_estudiantes()
        if estudiantes:
            face_recognition_processor.generar_encodings_desde_fotos(estudiantes)
        else:
            logger.warning("No hay estudiantes en la base de datos")

    logger.info(f"Servidor listo - ThreadPoolExecutor con {ASYNC_WORKERS} workers")

    yield  # Aquí corre la aplicación

    # SHUTDOWN
    logger.info("Cerrando servidor...")

    # Cerrar todas las conexiones WebSocket de dispositivos
    for device_id, ws in list(active_websockets.items()):
        try:
            await ws.close()
            logger.info(f"Conexión WebSocket cerrada: {device_id}")
        except:
            pass

    # Cerrar todas las conexiones WebSocket de viewers
    for device_id, viewers in list(active_viewers.items()):
        for ws in viewers:
            try:
                await ws.close()
            except:
                pass
        logger.info(f"Viewers cerrados para {device_id}")

    # Cerrar ThreadPoolExecutor
    executor.shutdown(wait=True)
    logger.info("ThreadPoolExecutor cerrado")


# ====================================
# INICIALIZACIÓN DE FASTAPI
# ====================================

# Configurar rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan
)

# Agregar rate limiter a la app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ====================================
# MIDDLEWARE - CORS
# ====================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====================================
# THREAD POOL EXECUTOR
# ====================================

# ThreadPoolExecutor para procesamiento asíncrono
executor = ThreadPoolExecutor(max_workers=ASYNC_WORKERS)

# ====================================
# MODELOS PYDANTIC
# ====================================


class FrameRequest(BaseModel):
    """Request model para procesamiento de frames"""
    image: str  # Base64 encoded image
    device_id: str


class RegistroRequest(BaseModel):
    """Request model para registro manual de asistencia"""
    id_estudiante: int
    device_id: Optional[str] = None


# ====================================
# CACHE Y ESTADO
# ====================================

# Cache para IPs de dispositivos (evitar consultas constantes)
dispositivos_cache: Dict[str, str] = {}

# Gestor de conexiones WebSocket activas (dispositivos IoT)
active_websockets: Dict[str, WebSocket] = {}

# Gestor de conexiones WebSocket de viewers (frontend)
# Formato: {device_id: [WebSocket, WebSocket, ...]}
active_viewers: Dict[str, List[WebSocket]] = {}


# ====================================
# FUNCIONES AUXILIARES
# ====================================


def limpiar_filename(nombre: str) -> str:
    """
    Convierte 'Matías Cataldo' en 'matias_cataldo.jpg'

    Args:
        nombre: Nombre completo del estudiante

    Returns:
        Nombre de archivo limpio y normalizado
    """
    nombre = nombre.lower()
    nombre = re.sub(r'[^\w\s-]', '', nombre)  # Quita caracteres extraños
    nombre = re.sub(r'[-\s]+', '_', nombre).strip('_')  # Reemplaza espacios y guiones
    return f"{nombre}.jpg"


async def enviar_comando_websocket(device_id: str, comando: Dict) -> bool:
    """
    Envía comando a un dispositivo a través de WebSocket

    Args:
        device_id: ID del dispositivo
        comando: Diccionario con el comando a enviar

    Returns:
        True si se envió exitosamente, False en caso contrario

    Note:
        Esta función reemplaza el antiguo sistema HTTP que no funcionaba
        en redes externas. Los dispositivos ahora mantienen una conexión
        WebSocket activa para recibir comandos en tiempo real.
    """
    if device_id not in active_websockets:
        logger.warning(f"WebSocket no activo para dispositivo: {device_id}")
        return False

    try:
        websocket = active_websockets[device_id]
        await websocket.send_json(comando)
        logger.info(f"Comando enviado a {device_id}: {comando}")
        return True
    except Exception as e:
        logger.error(f"Error al enviar comando WebSocket a {device_id}: {e}")
        # Limpiar conexión inactiva
        if device_id in active_websockets:
            del active_websockets[device_id]
        return False


# ====================================
# EVENTOS DE CICLO DE VIDA
# ====================================




# ====================================
# ENDPOINTS - INFORMACIÓN
# ====================================


@app.get("/")
async def root():
    """Endpoint raíz con información del sistema"""
    return {
        "sistema": APP_NAME,
        "version": APP_VERSION,
        "estado": "activo",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "procesar_frame": "POST /api/procesar-frame",
            "estudiantes": "GET /api/estudiantes",
            "asistencia_hoy": "GET /api/asistencia/hoy",
            "registrar": "POST /api/registrar",
            "nuevo_estudiante": "POST /api/estudiantes/nuevo",
            "recargar_encodings": "POST /api/recargar-encodings",
            "health": "GET /api/health",
            "websocket": "WS /ws/{device_id}"
        },
        "conexiones_activas": len(active_websockets)
    }


@app.get("/api/health")
@limiter.limit(RATE_LIMIT_READ)
async def health_check(request: Request):
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "encodings_loaded": face_recognition_processor.encodings_loaded,
        "total_encodings": len(face_recognition_processor.known_encodings),
        "websockets_activos": len(active_websockets),
        "dispositivos_conectados": list(active_websockets.keys())
    }


# ====================================
# ENDPOINTS - PROCESAMIENTO
# ====================================


@app.post("/api/procesar-frame")
@limiter.limit(RATE_LIMIT_PROCESS_FRAME)
async def procesar_frame(request: Request, frame_request: FrameRequest):
    """
    Procesa un frame recibido de la Raspberry Pi

    Args:
        frame_request: FrameRequest con imagen en base64 y device_id

    Returns:
        JSON con resultado del procesamiento y reconocimiento
    """
    try:
        device_id = frame_request.device_id

        # Decodificar imagen
        img_array = face_recognition_processor.decode_image_from_base64(frame_request.image)

        if img_array is None:
            raise HTTPException(status_code=400, detail="Error al decodificar imagen")

        # Procesar frame (se ejecuta en el thread pool para no bloquear)
        loop = asyncio.get_event_loop()
        resultado = await loop.run_in_executor(
            executor,
            face_recognition_processor.procesar_frame,
            img_array
        )

        if resultado['faces_found'] == 0:
            return {
                "status": "no_face",
                "message": "No se detectaron rostros"
            }

        # Si hay coincidencias (matches)
        if len(resultado['matches']) > 0:
            match = resultado['matches'][0]
            id_estudiante = match['id']
            nombre = match['name']
            confidence = match['confidence']

            # Verificar cooldown
            en_cooldown = db.verificar_cooldown(id_estudiante, COOLDOWN_SECONDS)

            if not en_cooldown:
                # Registrar asistencia
                registro = db.registrar_asistencia(id_estudiante, device_id)

                if registro['success']:
                    # Enviar comando de LED verde por WebSocket
                    await enviar_comando_websocket(device_id, {
                        "type": "led_control",
                        "color": "green",
                        "duration": 2
                    })

                    logger.info(f"Asistencia registrada: {nombre} (ID: {id_estudiante})")

                    return {
                        "status": "recognized",
                        "nombre": nombre,
                        "id_estudiante": id_estudiante,
                        "confidence": confidence,
                        "registrado": True,
                        "resultado": registro['resultado']
                    }
                else:
                    logger.error(f"Error al registrar: {registro.get('error')}")
                    return {
                        "status": "error",
                        "message": "Error al registrar en BD"
                    }
            else:
                # Ya fue registrado recientemente
                logger.info(f"{nombre} ya registrado (cooldown activo)")
                return {
                    "status": "recognized",
                    "nombre": nombre,
                    "id_estudiante": id_estudiante,
                    "confidence": confidence,
                    "registrado": False,
                    "mensaje": "Ya registrado hoy"
                }

        # No se reconoció ningún rostro
        await enviar_comando_websocket(device_id, {
            "type": "led_control",
            "color": "red",
            "duration": 1
        })

        return {
            "status": "unknown",
            "message": "Rostro no reconocido",
            "faces_found": resultado['faces_found']
        }

    except Exception as e:
        logger.error(f"Error procesando frame: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ====================================
# ENDPOINTS - ESTUDIANTES
# ====================================


@app.get("/api/estudiantes")
@limiter.limit(RATE_LIMIT_READ)
async def obtener_estudiantes(request: Request):
    """
    Obtiene la lista completa de estudiantes registrados
    """
    try:
        estudiantes = db.obtener_estudiantes()
        return {
            "total": len(estudiantes),
            "estudiantes": estudiantes
        }
    except Exception as e:
        logger.error(f"Error obteniendo estudiantes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/estudiantes/nuevo")
@limiter.limit(RATE_LIMIT_WRITE)
async def agregar_nuevo_estudiante(
    request: Request,
    nombre_completo: str = Form(...),
    rut: str = Form(None),
    foto: UploadFile = File(...)
):
    """
    Agrega un nuevo estudiante:
    1. Guarda la foto.
    2. Guarda en la BD.
    3. Recarga los encodings automáticamente.

    Args:
        nombre_completo: Nombre completo del estudiante
        rut: RUT del estudiante (opcional)
        foto: Archivo de foto del estudiante

    Returns:
        JSON con información del estudiante creado
    """
    # Preparar el nombre del archivo y la ruta
    filename = limpiar_filename(nombre_completo)
    filepath = os.path.join(str(PHOTOS_DIR), filename)

    try:
        # Guardar la foto en la carpeta /photos/student_photos/
        with open(filepath, "wb") as buffer:
            buffer.write(await foto.read())
        logger.info(f"Foto guardada en: {filepath}")

        # Guardar el estudiante en la BD
        nuevo_estudiante = db.crear_estudiante(nombre_completo, rut, filename)

        if not nuevo_estudiante:
            # Si falla la BD, borramos la foto que acabamos de guardar
            if os.path.exists(filepath):
                os.remove(filepath)
            raise HTTPException(
                status_code=409,
                detail="Error al guardar en BD (posible RUT duplicado)"
            )

        logger.info(f"Estudiante '{nombre_completo}' guardado en BD.")

        # Recargar encodings automáticamente
        logger.info("Recargando encodings...")
        await recargar_encodings_internal()

        return {"status": "ok", "estudiante": nuevo_estudiante}

    except HTTPException:
        raise
    except Exception as e:
        # Si algo falla, borrar la foto que acabamos de guardar
        if os.path.exists(filepath):
            os.remove(filepath)
        logger.error(f"Error en /api/estudiantes/nuevo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ====================================
# ENDPOINTS - ASISTENCIA
# ====================================


@app.get("/api/asistencia/hoy")
@limiter.limit(RATE_LIMIT_READ)
async def obtener_asistencia_hoy(request: Request):
    """
    Obtiene los registros de asistencia del día actual
    """
    try:
        asistencias = db.obtener_asistencia_hoy()
        return {
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "total": len(asistencias),
            "asistencias": asistencias
        }
    except Exception as e:
        logger.error(f"Error obteniendo asistencia: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/devices")
@limiter.limit(RATE_LIMIT_READ)
async def obtener_dispositivos(request: Request):
    """
    Obtiene la lista de dispositivos (Raspberries) registrados con sus IPs

    Returns:
        JSON con lista de dispositivos activos
    """
    try:
        dispositivos = []

        for device_id, ip in dispositivos_cache.items():
            # Verificar si está conectado por WebSocket
            is_online = device_id in active_websockets

            # Obtener último registro de este dispositivo
            ultimo_registro = None
            try:
                asistencias = db.obtener_asistencia_hoy()
                registros_dispositivo = [a for a in asistencias if a.get('dispositivo_id') == device_id]
                if registros_dispositivo:
                    ultimo_registro = registros_dispositivo[0]['hora_ingreso']
            except:
                pass

            dispositivos.append({
                "device_id": device_id,
                "ip": ip,
                "status": "online" if is_online else "offline",
                "stream_url": f"http://{ip}:8080/video_feed",
                "last_seen": datetime.now().isoformat() if is_online else None,
                "ultimo_registro": ultimo_registro
            })

        return {
            "total": len(dispositivos),
            "dispositivos": dispositivos,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error obteniendo dispositivos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/registrar")
@limiter.limit(RATE_LIMIT_WRITE)
async def registrar_manual(request: Request, registro_request: RegistroRequest):
    """
    Endpoint para registrar asistencia manualmente (legacy/backup)

    Args:
        registro_request: RegistroRequest con id_estudiante y device_id

    Returns:
        JSON con información del registro
    """
    try:
        resultado = db.registrar_asistencia(
            registro_request.id_estudiante,
            registro_request.device_id
        )

        if resultado['success']:
            estudiante = db.obtener_estudiante_por_id(registro_request.id_estudiante)
            return {
                "success": True,
                "estudiante": estudiante,
                "resultado": resultado['resultado']
            }
        else:
            raise HTTPException(status_code=400, detail=resultado.get('error'))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en registro manual: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ====================================
# ENDPOINTS - ENCODINGS
# ====================================


async def recargar_encodings_internal():
    """Función interna para recargar encodings (sin rate limiting)"""
    estudiantes = db.obtener_estudiantes()
    face_recognition_processor.generar_encodings_desde_fotos(estudiantes)


@app.post("/api/recargar-encodings")
@limiter.limit(RATE_LIMIT_WRITE)
async def recargar_encodings(request: Request):
    """
    Recarga los encodings desde las fotos
    Útil cuando se agregan nuevos estudiantes

    Returns:
        JSON con información de encodings cargados
    """
    try:
        await recargar_encodings_internal()

        return {
            "success": True,
            "message": f"Encodings recargados: {len(face_recognition_processor.known_encodings)} rostros"
        }
    except Exception as e:
        logger.error(f"Error recargando encodings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ====================================
# WEBSOCKET - DISPOSITIVOS IoT
# ====================================


@app.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: str):
    """
    WebSocket endpoint para mantener conexión con dispositivos IoT

    Args:
        device_id: ID único del dispositivo (ej: "rpi_001")

    Note:
        Este endpoint reemplaza el sistema HTTP anterior que no funcionaba
        en redes externas. Los dispositivos mantienen una conexión persistente
        para recibir comandos en tiempo real (control de LEDs, etc.)

    Protocol:
        - Client -> Server: {"type": "ping"} cada 30 segundos
        - Server -> Client: {"type": "pong"} respuesta a ping
        - Server -> Client: {"type": "led_control", "color": "green/red", "duration": 2}
    """
    await websocket.accept()
    active_websockets[device_id] = websocket
    logger.info(f"WebSocket conectado: {device_id} ({len(active_websockets)} conexiones activas)")

    try:
        while True:
            # Recibir mensajes del cliente (principalmente pings y video frames)
            data = await websocket.receive_json()

            if data.get("type") == "ping":
                # Responder con pong para mantener conexión viva
                await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})

            elif data.get("type") == "status":
                # El dispositivo puede enviar información de estado
                logger.info(f"Estado de {device_id}: {data}")

            elif data.get("type") == "video_frame":
                # Relay frame a todos los viewers conectados para este dispositivo
                if device_id in active_viewers and len(active_viewers[device_id]) > 0:
                    # Copiar lista para evitar problemas si se modifica durante iteración
                    viewers = active_viewers[device_id].copy()
                    disconnected_viewers = []

                    for viewer_ws in viewers:
                        try:
                            await viewer_ws.send_json(data)
                        except Exception as e:
                            logger.warning(f"Error enviando frame a viewer: {e}")
                            disconnected_viewers.append(viewer_ws)

                    # Limpiar viewers desconectados
                    for viewer_ws in disconnected_viewers:
                        if viewer_ws in active_viewers[device_id]:
                            active_viewers[device_id].remove(viewer_ws)

    except WebSocketDisconnect:
        logger.info(f"WebSocket desconectado: {device_id}")
    except Exception as e:
        logger.error(f"Error en WebSocket {device_id}: {e}")
    finally:
        # Limpiar conexión
        if device_id in active_websockets:
            del active_websockets[device_id]
        logger.info(f"Conexión cerrada: {device_id} ({len(active_websockets)} conexiones activas)")


@app.websocket("/ws/viewer/{device_id}")
async def websocket_viewer_endpoint(websocket: WebSocket, device_id: str):
    """
    WebSocket endpoint para viewers (frontend) que quieren ver el stream de una cámara

    Args:
        device_id: ID del dispositivo cuyo stream se quiere ver (ej: "rpi_001")

    Protocol:
        - Server -> Client: {"type": "video_frame", "frame": "base64...", "timestamp": "..."}
        - Server -> Client: {"type": "error", "message": "..."} si hay problemas

    Note:
        Los frames son relay desde el dispositivo IoT. Límite de MAX_VIEWERS_PER_DEVICE viewers simultáneos.
    """
    # Verificar límite de viewers
    if device_id in active_viewers and len(active_viewers[device_id]) >= MAX_VIEWERS_PER_DEVICE:
        await websocket.close(code=1008, reason=f"Límite de {MAX_VIEWERS_PER_DEVICE} viewers alcanzado")
        logger.warning(f"Viewer rechazado para {device_id}: límite de viewers alcanzado")
        return

    await websocket.accept()

    # Agregar viewer a la lista
    if device_id not in active_viewers:
        active_viewers[device_id] = []
    active_viewers[device_id].append(websocket)

    logger.info(f"Viewer conectado para {device_id} ({len(active_viewers[device_id])} viewers activos)")

    try:
        # Mantener conexión abierta
        while True:
            # Recibir mensajes del viewer (principalmente para mantener conexión viva)
            data = await websocket.receive_text()

            # El viewer puede enviar pings, pero no es necesario responder
            # Los frames se envían desde el device endpoint cuando llegan

    except WebSocketDisconnect:
        logger.info(f"Viewer desconectado de {device_id}")
    except Exception as e:
        logger.error(f"Error en viewer WebSocket para {device_id}: {e}")
    finally:
        # Limpiar viewer
        if device_id in active_viewers:
            if websocket in active_viewers[device_id]:
                active_viewers[device_id].remove(websocket)

            # Si no quedan viewers, eliminar entrada del dict
            if len(active_viewers[device_id]) == 0:
                del active_viewers[device_id]

        logger.info(f"Viewer removido de {device_id} ({len(active_viewers.get(device_id, []))} viewers restantes)")


# ====================================
# MIDDLEWARE - DEVICE IP CACHE
# ====================================


@app.middleware("http")
async def add_device_ip(request: Request, call_next):
    """
    Middleware para cachear IPs de dispositivos

    Note:
        Este middleware es principalmente legacy del sistema HTTP anterior.
        Con WebSockets ya no es tan necesario, pero se mantiene por compatibilidad.
    """
    response = await call_next(request)

    # Si es un request de procesar-frame, cachear la IP
    if request.url.path == "/api/procesar-frame":
        try:
            device_id = request.headers.get("X-Device-ID")
            if device_id:
                client_ip = request.client.host
                dispositivos_cache[device_id] = client_ip
        except Exception:
            pass

    return response


# ====================================
# ENTRY POINT
# ====================================


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════╗
    ║      SERVIDOR DE ASISTENCIA IoT - v2.0           ║
    ║        Reconocimiento Facial Centralizado        ║
    ╚═══════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        app,
        host=SERVER_HOST,
        port=SERVER_PORT,
        log_level=LOG_LEVEL.lower()
    )
