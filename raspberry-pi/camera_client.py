"""
pi_client_stream.py - OPTIMIZADO PARA FLUIDEZ
"""

import time
import base64
import requests
import logging
from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput
import RPi.GPIO as GPIO
from flask import Flask, Response
import threading
import io
import asyncio
import json
try:
    import websockets
    WS_AVAILABLE = True
except ImportError:
    WS_AVAILABLE = False
    print("⚠️ websockets no disponible - Instalarlo con: pip install websockets")

from config import (
    SERVER_URL, DEVICE_ID, FRAME_WIDTH, FRAME_HEIGHT,
    CAPTURE_INTERVAL, REQUEST_TIMEOUT,
    LED_GREEN_PIN, LED_RED_PIN, LED_DURATION,
    ENABLE_WEB_STREAM, WEB_STREAM_PORT,
    ENABLE_WS_STREAMING, WS_STREAM_FPS, WS_URL, WS_RECONNECT_DELAY
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)


class StreamingOutput(io.BufferedIOBase):
    """Buffer circular para frames de video"""
    def __init__(self):
        self.frame = None
        self.condition = threading.Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


class PiCliente:
    def __init__(self):
        """Inicializar cámara Pi, GPIO y configuración"""
        logger.info("🔌 Inicializando GPIO...")
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(LED_GREEN_PIN, GPIO.OUT)
        GPIO.setup(LED_RED_PIN, GPIO.OUT)
        GPIO.output(LED_GREEN_PIN, GPIO.LOW)
        GPIO.output(LED_RED_PIN, GPIO.LOW)

        logger.info("🎥 Inicializando cámara (Picamera2)...")
        self.camera = Picamera2()
        
        # Configuración de video (más eficiente que still)
        config = self.camera.create_video_configuration(
            main={"size": (FRAME_WIDTH, FRAME_HEIGHT)},
            controls={"FrameRate": 30}  # 30 FPS
        )
        
        self.camera.configure(config)
        
        # Usar encoder JPEG con streaming output
        self.output = StreamingOutput()
        self.encoder = JpegEncoder()
        
        self.camera.start_recording(self.encoder, FileOutput(self.output))
        time.sleep(1)

        self.server_url = f"{SERVER_URL}/api/procesar-frame"
        self.device_id = DEVICE_ID
        self.frame_count = 0
        self.last_send_time = 0

        logger.info(f"✅ Cámara inicializada: {FRAME_WIDTH}x{FRAME_HEIGHT} @ 30fps")
        logger.info(f"🌐 Servidor: {SERVER_URL}")
        logger.info(f"🔖 Device ID: {DEVICE_ID}")

    def control_led(self, color: str, duration: int):
        """Enciende un LED por una duración específica (sin bloquear)"""
        def _led_task():
            pin = LED_GREEN_PIN if color == 'green' else LED_RED_PIN
            GPIO.output(pin, GPIO.HIGH)
            time.sleep(duration)
            GPIO.output(pin, GPIO.LOW)
        
        # Ejecutar en thread separado para no bloquear
        threading.Thread(target=_led_task, daemon=True).start()

    def get_frame(self):
        """Obtiene el frame más reciente"""
        with self.output.condition:
            self.output.condition.wait()
            return self.output.frame

    def enviar_frame_async(self, jpeg_bytes):
        """Envía frame al servidor de forma asíncrona"""
        def _send():
            try:
                img_base64 = base64.b64encode(jpeg_bytes).decode('utf-8')
                payload = {"image": img_base64, "device_id": self.device_id}
                headers = {"Content-Type": "application/json", "X-Device-ID": self.device_id}

                response = requests.post(
                    self.server_url,
                    json=payload,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT
                )

                if response.status_code == 200:
                    respuesta = response.json()
                    self.procesar_respuesta(respuesta)

            except Exception as e:
                pass  # Silenciar errores para no afectar fluidez

        # Enviar en thread separado
        threading.Thread(target=_send, daemon=True).start()

    def procesar_respuesta(self, respuesta):
        """Procesa la respuesta del servidor y controla los LEDs"""
        if not respuesta:
            return

        status = respuesta.get('status')

        if status == 'recognized':
            nombre = respuesta.get('nombre', 'Desconocido')
            registrado = respuesta.get('registrado', False)
            if registrado:
                logger.info(f"✅ REGISTRADO: {nombre}")
                self.control_led("green", LED_DURATION)
            else:
                logger.info(f"✅ RECONOCIDO: {nombre}")

        elif status == 'unknown':
            logger.info("👤 DESCONOCIDO")
            self.control_led("red", 1)

        elif status == 'error':
            self.control_led("red", LED_DURATION)

    async def stream_video_websocket(self):
        """
        Streaming de video via WebSocket para frontend
        Envía frames a 0.5 FPS (cada 2 segundos) y mantiene conexión viva con pings
        """
        if not WS_AVAILABLE:
            logger.warning("WebSocket streaming deshabilitado: librería websockets no disponible")
            return

        ws_url = f"{WS_URL}/{DEVICE_ID}"
        logger.info(f"🔌 Iniciando WebSocket streaming a: {ws_url}")

        while True:
            try:
                async with websockets.connect(ws_url) as websocket:
                    logger.info(f"✅ WebSocket conectado para streaming")

                    last_frame_time = 0
                    last_ping_time = 0
                    frame_interval = 1.0 / WS_STREAM_FPS  # Intervalo entre frames
                    ping_interval = 30  # Ping cada 30 segundos

                    async def receive_messages():
                        """Task para recibir mensajes del servidor"""
                        try:
                            while True:
                                mensaje = await websocket.recv()
                                data = json.loads(mensaje)

                                if data.get("type") == "pong":
                                    logger.debug(f"Pong recibido del servidor")
                                elif data.get("type") == "led_control":
                                    # Controlar LED si el servidor envía comando
                                    color = data.get("color", "green")
                                    duration = data.get("duration", 2)
                                    self.control_led(color, duration)
                        except Exception as e:
                            logger.debug(f"Listener terminado: {e}")

                    # Iniciar task de recepción de mensajes
                    receive_task = asyncio.create_task(receive_messages())

                    try:
                        while True:
                            current_time = time.time()

                            # Enviar ping para mantener conexión viva
                            if current_time - last_ping_time >= ping_interval:
                                await websocket.send(json.dumps({"type": "ping"}))
                                last_ping_time = current_time
                                logger.debug("Ping enviado")

                            # Enviar frame solo si pasó el intervalo
                            if current_time - last_frame_time >= frame_interval:
                                frame = self.get_frame()
                                if frame:
                                    # Codificar a base64
                                    frame_b64 = base64.b64encode(frame).decode('utf-8')

                                    # Crear mensaje
                                    mensaje = {
                                        "type": "video_frame",
                                        "frame": frame_b64,
                                        "timestamp": current_time,
                                        "device_id": DEVICE_ID
                                    }

                                    # Enviar
                                    await websocket.send(json.dumps(mensaje))
                                    last_frame_time = current_time
                                    logger.debug(f"Frame enviado ({len(frame_b64)} bytes)")

                            # Pequeña pausa para no saturar
                            await asyncio.sleep(0.1)
                    finally:
                        # Cancelar task de recepción al salir
                        receive_task.cancel()

            except websockets.exceptions.WebSocketException as e:
                logger.error(f"❌ Error WebSocket streaming: {e}")
                logger.info(f"🔄 Reconectando en {WS_RECONNECT_DELAY} segundos...")
                await asyncio.sleep(WS_RECONNECT_DELAY)
            except Exception as e:
                logger.error(f"❌ Error inesperado en WebSocket streaming: {e}")
                await asyncio.sleep(WS_RECONNECT_DELAY)

    def run(self):
        """Bucle principal de captura y envío"""
        logger.info("\n" + "="*50)
        logger.info("🚀 STREAMING ACTIVO @ 30 FPS")
        logger.info("="*50 + "\n")

        # Iniciar WebSocket streaming en thread separado si está habilitado
        if ENABLE_WS_STREAMING and WS_AVAILABLE:
            def run_ws_streaming():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.stream_video_websocket())

            ws_thread = threading.Thread(target=run_ws_streaming, daemon=True)
            ws_thread.start()
            logger.info(f"📡 WebSocket streaming iniciado ({WS_STREAM_FPS} FPS)")

        try:
            while True:
                self.frame_count += 1

                # Enviar al servidor cada 1 segundo (no cada frame)
                current_time = time.time()
                if current_time - self.last_send_time >= CAPTURE_INTERVAL:
                    frame = self.get_frame()
                    if frame:
                        self.enviar_frame_async(frame)
                        self.last_send_time = current_time

                if self.frame_count % 100 == 0:
                    logger.info(f"📊 Frames: {self.frame_count}")

                time.sleep(0.001)  # Pequeña pausa para no saturar CPU

        except KeyboardInterrupt:
            logger.info("\n⚠️ Deteniendo...")
        finally:
            self.cleanup()

    def cleanup(self):
        """Limpieza al cerrar"""
        logger.info("🧹 Liberando recursos...")
        try:
            self.camera.stop_recording()
            self.camera.stop()
            self.camera.close()
            logger.info("✅ Cámara cerrada")
        except:
            pass
        try:
            GPIO.cleanup()
            logger.info("✅ GPIO limpiado")
        except:
            pass


# Instancia global
cliente = None

@app.route('/')
def index():
    """Página principal optimizada"""
    return """
    <html>
    <head>
        <title>Pi Camera Stream</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                background: #000;
                color: #0f0;
                font-family: monospace;
                text-align: center;
                padding: 10px;
                margin: 0;
            }
            img {
                max-width: 100%;
                border: 2px solid #0f0;
                image-rendering: auto;
            }
            h1 { margin: 10px 0; font-size: 1.2em; }
        </style>
    </head>
    <body>
        <h1>🎥 Live Stream - """ + DEVICE_ID + """</h1>
        <img src="/video_feed" />
    </body>
    </html>
    """

@app.route('/video_feed')
def video_feed():
    """Endpoint de streaming MJPEG optimizado"""
    def generate():
        while True:
            if cliente and cliente.output:
                frame = cliente.get_frame()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    
    return Response(generate(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


def main():
    """Función principal"""
    global cliente

    print("""
    ╔═══════════════════════════════════════════════════╗
    ║        RASPBERRY PI CAMERA CLIENT v2.0            ║
    ║    Stream: 30 FPS | Server: cada 2 segundos       ║
    ╚═══════════════════════════════════════════════════╝
    """)

    try:
        cliente = PiCliente()

        # Servidor Flask CONDICIONAL para monitoreo desde dashboard
        if ENABLE_WEB_STREAM:
            flask_thread = threading.Thread(
                target=lambda: app.run(
                    host='0.0.0.0',
                    port=WEB_STREAM_PORT,
                    threaded=True,
                    debug=False,
                    use_reloader=False
                )
            )
            flask_thread.daemon = True
            flask_thread.start()

            logger.info(f"🌐 Stream disponible en: http://<IP-RASPBERRY>:{WEB_STREAM_PORT}")
            logger.info("   (Para consumir desde dashboard centralizado)")
        else:
            logger.info("📺 Stream web deshabilitado (ENABLE_WEB_STREAM=false)")

        cliente.run()

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        try:
            GPIO.cleanup()
        except:
            pass

if __name__ == "__main__":
    main()
