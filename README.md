# 🎯 Sistema de Asistencia con Reconocimiento Facial IoT

> Sistema profesional de control de asistencia mediante reconocimiento facial, con arquitectura distribuida usando FastAPI, Raspberry Pi, MySQL y WebSockets en tiempo real.

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.120.0-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Desarrollado por:** Matías Cataldo
**Stack:** Python, FastAPI, MySQL, Raspberry Pi, WebSockets, Face Recognition (dlib)

---

## 📋 Tabla de Contenidos

- [Características](#-características)
- [Demo en Vivo](#-demo-en-vivo)
- [Arquitectura](#-arquitectura)
- [Requisitos](#-requisitos)
- [Instalación Rápida](#-instalación-rápida)
- [Configuración](#-configuración)
- [Uso](#-uso)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Marco Legal y Privacidad](#-marco-legal-y-privacidad)
- [Roadmap](#-roadmap)
- [Licencia](#-licencia)

---

## ✨ Características

### 🚀 Funcionalidades Principales

- ✅ **Reconocimiento facial en tiempo real** con precisión del 96%+ (face_recognition + dlib)
- ✅ **Streaming de video WebSocket** a 3 FPS para monitoreo centralizado
- ✅ **Dashboard web interactivo** con estadísticas en tiempo real
- ✅ **Sistema multi-dispositivo** (soporta múltiples Raspberry Pi simultáneamente)
- ✅ **Registro automático de asistencia** con cooldown anti-duplicados (configurable)
- ✅ **Gestión de estudiantes** con captura de foto desde webcam
- ✅ **WebSockets bidireccionales** para control de LEDs remotos (feedback visual)
- ✅ **Base de datos MySQL** con Docker Compose para desarrollo
- ✅ **API RESTful documentada** con OpenAPI/Swagger automático
- ✅ **Auto-inicio con systemd** para servidor y Raspberry Pi

### 🔒 Seguridad y Privacidad

- 🔐 **Minimización de datos**: Fotos se eliminan automáticamente después de generar encodings (configurable)
- 🔐 **Conexiones cifradas**: HTTPS/WSS en todas las comunicaciones
- 🔐 **Cumplimiento legal**: Ley 19.628 Chile (Protección de Datos Personales)
- 🔐 **Sistema opt-in**: Consentimiento informado requerido
- 🔐 **Derecho al olvido**: Eliminación completa de datos biométricos
- 🔐 **Encodings irreversibles**: Vectores matemáticos 128D no pueden revertirse a fotos

### 📊 Métricas y Reportes

- 📈 **Estadísticas en tiempo real**: Asistencia del día, total de estudiantes
- 📈 **Historial detallado**: Fecha, hora, dispositivo de registro
- 📈 **Filtros avanzados**: Por fecha, estudiante, dispositivo
- 📈 **Monitor de cámaras**: Ver stream en vivo de todas las Raspberry Pi
- 📈 **Detección de estado**: Dispositivos online/offline en tiempo real

### ⚡ Performance

- 🚄 **Procesamiento asíncrono**: ThreadPoolExecutor + asyncio
- 🚄 **Rate limiting**: Protección contra sobrecarga (100 req/min por endpoint)
- 🚄 **Caché inteligente**: IPs de dispositivos cacheadas en memoria
- 🚄 **Reconexión automática**: WebSockets con backoff exponencial
- 🚄 **Streaming optimizado**: 0.5 FPS para reconocimiento, 3 FPS para monitoreo

---

## 🎬 Demo en Vivo

**URL del sistema:** [Tu dominio aquí]

**Credenciales de demo:**
- Usuario: `demo`
- Password: `demo123`

**Funcionalidades disponibles:**
1. Dashboard con estadísticas en tiempo real
2. Registro de nuevos estudiantes con webcam
3. Monitor de cámaras en vivo
4. Historial de asistencia

---

## 🏗️ Arquitectura

### **Diagrama de Componentes**

```
┌─────────────────────────────────────────────────────────────┐
│                    SERVIDOR BACKEND (Público)               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              FastAPI + Uvicorn                        │  │
│  │  ┌─────────────────┐  ┌──────────────────────────┐   │  │
│  │  │   API REST      │  │   WebSocket Server       │   │  │
│  │  │   - /api/...    │  │   - /ws/{device_id}      │   │  │
│  │  │   - Rate limit  │  │   - /ws/viewer/{id}      │   │  │
│  │  └─────────────────┘  └──────────────────────────┘   │  │
│  │                                                         │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │   Face Recognition Processor                    │  │  │
│  │  │   - face_recognition library (dlib)             │  │  │
│  │  │   - ThreadPoolExecutor (async)                  │  │  │
│  │  │   - Tolerancia: 0.6 (configurable)              │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────┬───────────────────────────────┘  │
│                          │                                   │
│  ┌───────────────────────▼────────────┐  ┌───────────────┐ │
│  │   MySQL Database (Docker)          │  │  Encodings    │ │
│  │   - estudiantes                    │  │  (pickle)     │ │
│  │   - asistencia                     │  │  128D vectors │ │
│  └────────────────────────────────────┘  └───────────────┘ │
└──────────────────┬──────────────────────────────────────────┘
                   │ HTTPS/WSS
                   │
       ┌───────────▼──────────────┬─────────────────────┐
       │                          │                     │
┌──────▼──────────┐  ┌────────────▼────────┐  ┌────────▼─────────┐
│  RASPBERRY PI 1 │  │  RASPBERRY PI 2     │  │  WEB DASHBOARD   │
│  (Red privada)  │  │  (Red privada)      │  │  (Navegador)     │
│ ┌─────────────┐ │  │ ┌─────────────┐    │  │ ┌──────────────┐ │
│ │Camera Client│ │  │ │Camera Client│    │  │ │ index.html   │ │
│ │- PiCamera2  │ │  │ │- PiCamera2  │    │  │ │ monitor.html │ │
│ │- WebSocket  │ │  │ │- WebSocket  │    │  │ │ add-student  │ │
│ │- GPIO LEDs  │ │  │ │- GPIO LEDs  │    │  │ └──────────────┘ │
│ └─────────────┘ │  │ └─────────────┘    │  │ ┌──────────────┐ │
│ Flask (:8080)   │  │ Flask (:8080)      │  │ │ WebSocket    │ │
│ Local stream    │  │ Local stream       │  │ │ Client       │ │
└─────────────────┘  └────────────────────┘  └──────────────────┘
```

### **Flujo de Datos**

#### **1. Reconocimiento Facial (0.5 FPS)**
```
Raspberry Pi → Captura frame cada 2 seg
             ↓ HTTPS POST /api/procesar-frame
          Servidor → Face recognition (asyncio + ThreadPool)
             ↓ Si reconoce
          MySQL ← Registra asistencia (con cooldown check)
             ↓ WebSocket
Raspberry Pi ← Comando LED (verde=registrado, rojo=desconocido)
```

#### **2. Streaming de Video (3 FPS)**
```
Raspberry Pi → Frame base64 cada 0.33 seg
             ↓ WebSocket /ws/{device_id}
          Servidor → Relay a viewers
             ↓ WebSocket /ws/viewer/{device_id}
       Dashboard ← Muestra frame en <img>
```

#### **3. Gestión de Estudiantes**
```
Dashboard → Captura webcam
          ↓ POST /api/estudiantes/nuevo
    Servidor → Guarda foto → Genera encodings
          ↓ (Opcional) Elimina foto
       MySQL ← Registra estudiante
```

### **Tecnologías Utilizadas**

| Componente | Tecnología | Versión |
|------------|-----------|---------|
| **Backend** | FastAPI | 0.120.0 |
| **Server** | Uvicorn | 0.38.0 |
| **Base de Datos** | MySQL | 9.5.0 |
| **Face Recognition** | face_recognition | 1.3.0 |
| **Computer Vision** | dlib | 20.0.0 |
| **WebSockets** | websockets | 15.0.1 |
| **Edge Device** | Raspberry Pi 3/4 | - |
| **Camera** | PiCamera2 | 0.3.12+ |
| **GPIO Control** | RPi.GPIO | 0.7.1 |
| **Frontend** | Vanilla JS + HTML5 | - |
| **Reverse Proxy** | Nginx | 1.18+ |
| **Containerización** | Docker Compose | 2.0+ |
| **Sistema Operativo (Server)** | Ubuntu 20.04+ | - |
| **Sistema Operativo (Pi)** | Raspberry Pi OS | Bookworm |

---

## 📦 Requisitos

### **Servidor (Backend)**

- **Hardware:**
  - CPU: 2+ cores
  - RAM: 4GB mínimo, 8GB recomendado
  - Disco: 20GB SSD
  - Red: IP pública o dominio

- **Software:**
  - Ubuntu 20.04+ (o cualquier Linux)
  - Python 3.9+
  - Docker & Docker Compose
  - Nginx (opcional, para HTTPS)

### **Raspberry Pi (Edge Devices)**

- **Hardware:**
  - Raspberry Pi 3B+ o 4 (recomendado: Pi 4 con 4GB RAM)
  - PiCamera Module v2 o v3
  - Tarjeta microSD 16GB+ (Clase 10)
  - Fuente 5V 3A
  - LEDs RGB + resistencias 220Ω (opcional)

- **Software:**
  - Raspberry Pi OS (Bookworm o superior)
  - Python 3.9+
  - libcamera (incluido en Pi OS)

### **Cliente (Dashboard)**

- Navegador moderno (Chrome 90+, Firefox 88+, Safari 14+)
- Conexión a internet

---

## 🚀 Instalación Rápida

### **1. Clonar Repositorio**

```bash
git clone https://github.com/braIntelligent/facial-attendance-system.git
cd facial-attendance-system
```

### **2. Instalar Servidor**

```bash
cd server

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
nano .env  # Editar con tus credenciales

# Iniciar MySQL con Docker
docker-compose up -d

# Inicializar base de datos
python init_db.py

# Instalar servicio systemd (opcional, para auto-inicio)
sudo cp attendance-server.service /etc/systemd/system/
sudo systemctl enable attendance-server
sudo systemctl start attendance-server
```

Ver guía completa: [`server/README.md`](server/README.md)

### **3. Instalar Raspberry Pi**

```bash
# En cada Raspberry Pi
git clone https://github.com/braIntelligent/facial-attendance-system.git
cd facial-attendance-system/raspberry-pi

# Instalar dependencias
pip3 install --break-system-packages -r requirements.txt

# Configurar
cp .env.example .env
nano .env  # Configurar SERVER_HOST y DEVICE_ID

# Instalar servicio systemd (para auto-inicio)
sudo cp camera-client.service /etc/systemd/system/
sudo systemctl enable camera-client
sudo systemctl start camera-client
```

Ver guía completa: [`raspberry-pi/README.md`](raspberry-pi/README.md)

### **4. Configurar Frontend**

```bash
# Copiar al directorio web de Nginx
sudo cp -r web-dashboard/* /var/www/html/

# Configurar Nginx (ver nginx.conf.example)
sudo nano /etc/nginx/sites-available/default

# Recargar Nginx
sudo nginx -t
sudo systemctl reload nginx
```

---

## ⚙️ Configuración

### **Variables de Entorno - Servidor**

```bash
# Base de Datos
DB_HOST=localhost
DB_USER=asistencia_user
DB_PASS=tu_password_seguro
DB_NAME=asistencia_db

# Servidor
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# Seguridad
SECRET_KEY=genera_con_secrets.token_hex(32)

# Reconocimiento Facial
FACE_TOLERANCE=0.6  # 0.0-1.0 (más bajo = más estricto)
FACE_DETECTION_MODEL=hog  # hog (rápido) o cnn (preciso)
COOLDOWN_SECONDS=300  # Cooldown entre registros del mismo estudiante

# Privacidad (Ley 19.628)
KEEP_PHOTOS_AFTER_ENCODING=false  # false = elimina fotos (recomendado)

# WebSocket
MAX_VIEWERS_PER_DEVICE=5  # Viewers simultáneos por cámara
```

### **Variables de Entorno - Raspberry Pi**

```bash
# Servidor
SERVER_HOST=tu-dominio.com
SERVER_PROTOCOL=https

# Identificación
DEVICE_ID=pi-aula-101  # ID único para cada Pi

# Cámara
FRAME_WIDTH=640
FRAME_HEIGHT=480
JPEG_QUALITY=70

# Reconocimiento Facial
CAPTURE_INTERVAL=2.0  # Segundos entre envíos al servidor

# Streaming WebSocket
ENABLE_WS_STREAMING=true
WS_STREAM_FPS=3.0  # FPS para monitor (1-5 recomendado)

# GPIO
LED_GREEN_PIN=17
LED_RED_PIN=27

# Stream Local (opcional)
ENABLE_WEB_STREAM=true
WEB_STREAM_PORT=8080
```

---

## 📖 Uso

### **1. Agregar Estudiantes**

1. Ir a: `https://tu-dominio.com/views/add-student.html`
2. Ingresar RUT, nombre completo y email
3. Capturar foto con webcam (asegurar buena iluminación)
4. Enviar formulario
5. El sistema generará encodings automáticamente

### **2. Ver Dashboard**

1. Ir a: `https://tu-dominio.com/`
2. Ver estadísticas en tiempo real:
   - Total de estudiantes
   - Asistencias de hoy
   - Dispositivos conectados
3. Tabla con historial de registros

### **3. Monitorear Cámaras**

1. Ir a: `https://tu-dominio.com/views/monitor.html`
2. Seleccionar dispositivo de la lista
3. Click "Iniciar Stream"
4. Ver stream en tiempo real (3 FPS)

### **4. Gestión del Sistema**

```bash
# Ver logs del servidor
sudo journalctl -u attendance-server -f

# Ver logs de Raspberry Pi
sudo journalctl -u camera-client -f

# Reiniciar servicios
sudo systemctl restart attendance-server  # Servidor
sudo systemctl restart camera-client      # Raspberry Pi

# Ver estado
sudo systemctl status attendance-server
sudo systemctl status camera-client
```

---

## 📁 Estructura del Proyecto

```
facial-attendance-system/
├── server/                           # Backend FastAPI
│   ├── app/
│   │   ├── api/                      # Endpoints (futuro)
│   │   ├── core/
│   │   │   ├── database.py           # Operaciones MySQL
│   │   │   └── face_recognition.py   # Procesamiento facial
│   │   ├── models/
│   │   │   ├── student.py            # Modelo estudiante
│   │   │   ├── attendance.py         # Modelo asistencia
│   │   │   └── frame.py              # Modelo frames
│   │   ├── config.py                 # Configuración centralizada
│   │   └── main.py                   # FastAPI app principal
│   ├── data/
│   │   ├── photos/
│   │   │   ├── student_photos/       # Fotos originales (auto-eliminadas)
│   │   │   └── encodings.pkl         # Encodings faciales
│   │   └── logs/                     # Logs del servidor
│   ├── docker-compose.yml            # MySQL + phpMyAdmin
│   ├── schema.sql                    # Schema de BD
│   ├── init_db.py                    # Script de inicialización
│   ├── requirements.txt              # Dependencias Python
│   ├── attendance-server.service     # Servicio systemd
│   ├── INSTALL_SERVICE.md            # Guía instalación systemd
│   ├── .env.example                  # Template de configuración
│   └── README.md                     # Documentación servidor
│
├── raspberry-pi/                     # Cliente Raspberry Pi
│   ├── camera_client.py              # Cliente principal
│   ├── config.py                     # Configuración Pi
│   ├── requirements.txt              # Dependencias Python
│   ├── camera-client.service         # Servicio systemd
│   ├── INSTALL_SERVICE.md            # Guía instalación systemd
│   ├── TUNNEL_SSH.md                 # Guía túnel SSH
│   ├── .env.example                  # Template de configuración
│   └── README.md                     # Documentación Pi
│
├── web-dashboard/                    # Frontend
│   ├── views/
│   │   ├── index.html                # Dashboard principal
│   │   ├── add-student.html          # Formulario estudiantes
│   │   └── monitor.html              # Monitor de cámaras
│   └── assets/
│       ├── css/
│       │   └── styles.css            # Estilos globales
│       └── js/
│           ├── config.js             # Configuración frontend
│           ├── api.js                # Llamadas API centralizadas
│           ├── utils.js              # Utilidades comunes
│           ├── dashboard.js          # Lógica dashboard
│           ├── student-form.js       # Lógica formulario
│           └── monitor.js            # Lógica monitor
│
├── docs/                             # Documentación adicional
│   ├── DEFENSE.md                    # Argumentación legal/ética
│   └── ARCHITECTURE.md               # Arquitectura detallada
│
├── .gitignore                        # Archivos ignorados
├── LICENSE                           # Licencia MIT
└── README.md                         # Este archivo
```

---

## ⚖️ Marco Legal y Privacidad

Este proyecto cumple con la **Ley 19.628 de Chile** (Protección de Datos Personales):

### **Principios Aplicados**

1. **Consentimiento Informado**: Estudiantes deben autorizar explícitamente el uso de su imagen
2. **Minimización de Datos**: Solo se almacenan encodings matemáticos (no fotos originales)
3. **Finalidad Específica**: Sistema usado exclusivamente para control de asistencia
4. **Limitación Temporal**: Datos biométricos se eliminan al finalizar el semestre/curso
5. **Derecho al Olvido**: Usuarios pueden solicitar eliminación completa de sus datos

### **Alternativas No-Biométricas**

El sistema debe ofrecer siempre una alternativa manual:
- Registro con código QR
- Firma en lista tradicional
- Identificación con tarjeta RFID

### **Documentos Requeridos**

- ✅ Política de Privacidad ([ver template](docs/PRIVACY_POLICY.md))
- ✅ Formulario de Consentimiento ([ver template](docs/CONSENT_FORM.md))
- ✅ Evaluación de Impacto de Privacidad (DPIA)

Ver documentación completa: [`docs/DEFENSE.md`](docs/DEFENSE.md)

---

## 🗺️ Roadmap

### **v2.1 (En desarrollo)**
- [ ] Exportación de reportes (CSV, PDF)
- [ ] Notificaciones por email (ausencias)
- [ ] Multi-tenancy (múltiples instituciones)
- [ ] Análisis de patrones de asistencia

### **v2.2 (Futuro)**
- [ ] Aplicación móvil (React Native)
- [ ] Reconocimiento con máscara facial
- [ ] Integración con Google Calendar
- [ ] Dashboard con gráficos avanzados (Chart.js)

### **v3.0 (Largo plazo)**
- [ ] Machine Learning predictivo (detectar ausencias)
- [ ] Integración con sistemas académicos (LMS)
- [ ] Modo offline (sincronización diferida)
- [ ] Reconocimiento multi-factor (face + voz)

---

## 🤝 Contribución

¡Las contribuciones son bienvenidas! Por favor:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add: AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

**Guidelines:**
- Seguir PEP 8 para código Python
- Documentar funciones con docstrings
- Agregar tests cuando sea posible
- Actualizar documentación si es necesario

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver archivo [`LICENSE`](LICENSE) para más detalles.

```
MIT License

Copyright (c) 2024 Matías Cataldo

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```

---

## 📞 Contacto

**Matías Cataldo**
- GitHub: [@braIntelligent](https://github.com/braIntelligent)
- Email: [Tu email aquí]
- LinkedIn: [Tu perfil]

---

## 🙏 Agradecimientos

- **face_recognition** por la excelente librería de reconocimiento facial
- **dlib** por los modelos pre-entrenados
- **FastAPI** por el framework moderno y rápido
- Comunidad open-source por las herramientas utilizadas

---

## 📊 Estadísticas del Proyecto

- **Líneas de código:** ~5,000+
- **Lenguajes:** Python (80%), JavaScript (15%), HTML/CSS (5%)
- **Commits:** 50+
- **Tiempo de desarrollo:** 3+ semanas
- **Cobertura de tests:** En desarrollo

---

**⭐ Si este proyecto te fue útil, considera darle una estrella en GitHub!**

---

*Última actualización: 2025-01-11*
