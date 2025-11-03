// student-form.js - Logica del formulario de agregar estudiante

// Estado de la camara
let streamActivo = null;

// Elementos del DOM
let formAgregar;
let videoEl;
let canvasEl;
let fotoPreviewEl;
let btnIniciarCamara;
let btnCapturarFoto;
let btnGuardar;
let btnCancelar;
let inputNombre;
let inputRut;

// ==============================================
// INICIALIZACION
// ==============================================

// Validación básica de RUT chileno
function validarRut(rut) {
    // Limpiar puntos y guion
    rut = rut.replace(/\./g, '').replace(/-/g, '');
    if(rut.length < 2) return false;

    const cuerpo = rut.slice(0, -1);
    let dv = rut.slice(-1).toUpperCase();

    let suma = 0;
    let multiplo = 2;

    for (let i = cuerpo.length - 1; i >= 0; i--) {
        suma += parseInt(cuerpo.charAt(i)) * multiplo;
        multiplo = multiplo === 7 ? 2 : multiplo + 1;
    }

    const dvEsperado = 11 - (suma % 11);
    let dvCalculado = dvEsperado === 11 ? '0' : dvEsperado === 10 ? 'K' : dvEsperado.toString();

    return dv === dvCalculado;
}

// Elemento donde mostrar mensaje de validación
let rutFeedback = null;

// Inicialización al cargar la página
document.addEventListener('DOMContentLoaded', () => {
    // Obtener referencias del DOM
    formAgregar = document.getElementById('form-agregar-estudiante');
    videoEl = document.getElementById('webcam-preview');
    canvasEl = document.getElementById('webcam-canvas');
    fotoPreviewEl = document.getElementById('foto-preview');
    btnIniciarCamara = document.getElementById('btn-iniciar-camara');
    btnCapturarFoto = document.getElementById('btn-capturar-foto');
    btnGuardar = document.getElementById('btn-guardar-estudiante');
    btnCancelar = document.getElementById('btn-cancelar-agregar');
    inputNombre = document.getElementById('nombre-nuevo');
    inputRut = document.getElementById('rut-nuevo');

    // Crear span para feedback del RUT
    rutFeedback = document.createElement('span');
    rutFeedback.style.fontSize = '0.9em';
    rutFeedback.style.marginLeft = '8px';
    inputRut.parentNode.appendChild(rutFeedback);

    // Listener de RUT en tiempo real
    inputRut.addEventListener('input', () => {
        const rutValido = validarRut(inputRut.value.trim());
        rutFeedback.textContent = rutValido ? '✔ RUT válido' : '❌ RUT inválido';
        rutFeedback.style.color = rutValido ? 'green' : 'red';
        // Habilitar botón guardar solo si todo es válido
        btnGuardar.disabled = !rutValido || !inputNombre.value.trim() || !fotoPreviewEl.src || fotoPreviewEl.src === window.location.href;
    });

    // Listener de nombre también
    inputNombre.addEventListener('input', () => {
        const rutValido = validarRut(inputRut.value.trim());
        btnGuardar.disabled = !rutValido || !inputNombre.value.trim() || !fotoPreviewEl.src || fotoPreviewEl.src === window.location.href;
    });

    // Configurar demás event listeners
    configurarEventListeners();
});

// ==============================================
// EVENT LISTENERS
// ==============================================

function configurarEventListeners() {
    if (btnIniciarCamara) {
        btnIniciarCamara.addEventListener('click', iniciarWebcam);
    }

    if (btnCapturarFoto) {
        btnCapturarFoto.addEventListener('click', tomarFoto);
    }

    if (btnCancelar) {
        btnCancelar.addEventListener('click', cancelarFormulario);
    }

    if (formAgregar) {
        formAgregar.addEventListener('submit', guardarEstudiante);
    }
}

// ==============================================
// FUNCIONES DE CAMARA
// ==============================================

/**
 * Inicia la camara web del usuario
 */
async function iniciarWebcam() {
    try {
        // Detener stream previo si existe
        if (streamActivo) {
            streamActivo.getTracks().forEach(track => track.stop());
        }

        streamActivo = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480 },
            audio: false
        });

        videoEl.srcObject = streamActivo;
        videoEl.style.display = 'block';
        fotoPreviewEl.style.display = 'none';
        btnIniciarCamara.style.display = 'none';
        btnCapturarFoto.style.display = 'block';
        btnGuardar.disabled = true;

    } catch (err) {
        console.error('Error al acceder a la camara:', err);
        mostrarToast('No se pudo acceder a la camara', 'error');
    }
}

/**
 * Detiene la camara web
 */
function detenerWebcam() {
    if (streamActivo) {
        streamActivo.getTracks().forEach(track => track.stop());
        streamActivo = null;
    }

    if (videoEl) {
        videoEl.srcObject = null;
        videoEl.style.display = 'none';
    }

    if (fotoPreviewEl) {
        fotoPreviewEl.style.display = 'none';
    }

    if (btnIniciarCamara) btnIniciarCamara.style.display = 'block';
    if (btnCapturarFoto) btnCapturarFoto.style.display = 'none';
    if (btnGuardar) btnGuardar.disabled = true;
}

/**
 * Captura una foto desde el video
 */
function tomarFoto() {
    if (!videoEl || !canvasEl || !fotoPreviewEl) {
        console.error('Elementos de camara no encontrados');
        return;
    }

    // Configurar el canvas al tamano del video
    canvasEl.width = videoEl.videoWidth;
    canvasEl.height = videoEl.videoHeight;

    // Dibujar el frame actual del video en el canvas
    const context = canvasEl.getContext('2d');
    context.drawImage(videoEl, 0, 0, canvasEl.width, canvasEl.height);

    // Mostrar la foto en el <img> de preview
    const dataUrl = canvasEl.toDataURL('image/jpeg');
    fotoPreviewEl.src = dataUrl;
    fotoPreviewEl.style.display = 'block';

    // Detener el video
    if (streamActivo) {
        streamActivo.getTracks().forEach(track => track.stop());
        streamActivo = null;
    }

    videoEl.srcObject = null;
    videoEl.style.display = 'none';
    btnCapturarFoto.style.display = 'none';
    btnIniciarCamara.style.display = 'block';
    btnGuardar.disabled = false; // Habilitar el boton de guardar
}

// ==============================================
// FUNCIONES DEL FORMULARIO
// ==============================================

/**
 * Guarda el estudiante con su foto
 */
async function guardarEstudiante(e) {
    e.preventDefault();

    const nombre = inputNombre.value.trim();
    const rut = inputRut.value.trim();

    if (!rut) {
    mostrarToast('El RUT es obligatorio', 'error');
    return;
    }

    if (!validarRut(rut)) {
        mostrarToast('El RUT ingresado es inválido', 'error');
        return;
    }

    if (!nombre) {
        mostrarToast('El nombre es obligatorio', 'error');
        return;
    }

    // Verificar que se haya capturado una foto
    if (!fotoPreviewEl.src || fotoPreviewEl.src === window.location.href) {
        mostrarToast('Debe capturar una foto del estudiante', 'error');
        return;
    }

    btnGuardar.disabled = true;
    btnGuardar.textContent = 'Guardando...';

    // Convertir la imagen del canvas a un Blob
    canvasEl.toBlob(async (blob) => {
        if (!blob) {
            mostrarToast('Error al procesar la imagen', 'error');
            btnGuardar.disabled = false;
            btnGuardar.textContent = 'Guardar Estudiante';
            return;
        }

        // Crear FormData para enviar la imagen
        const formData = new FormData();
        formData.append('nombre_completo', nombre);
        formData.append('rut', rut);
        formData.append('foto', blob, 'foto_estudiante.jpg');

        try {
            const data = await addStudent(formData);

            mostrarToast(`Estudiante '${data.estudiante.nombre_completo}' agregado`, 'success');

            // Redirigir al dashboard con mensaje de exito
            setTimeout(() => {
                window.location.href = 'index.html?success=true';
            }, 1000);

        } catch (error) {
            console.error('Error al guardar:', error);
            mostrarToast(error.message, 'error');
            btnGuardar.disabled = false;
            btnGuardar.textContent = 'Guardar Estudiante';
        }

    }, 'image/jpeg', 0.9);
}

/**
 * Cancela el formulario y vuelve al dashboard
 */
function cancelarFormulario() {
    if (confirm('¿Desea cancelar y volver al dashboard?')) {
        detenerWebcam();
        window.location.href = 'index.html';
    }
}

console.log('✅ Formulario de estudiante cargado');
