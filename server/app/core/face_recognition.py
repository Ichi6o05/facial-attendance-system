"""
face_recognition.py - Módulo de reconocimiento facial
Carga encodings y compara rostros usando face_recognition library
"""

import face_recognition
import numpy as np
import pickle
import os
import base64
from PIL import Image
import io
from typing import Dict, List, Optional, Any, Tuple
import logging

from app.config import (
    PHOTOS_DIR,
    ENCODINGS_FILE,
    FACE_TOLERANCE,
    FACE_DETECTION_MODEL,
    KEEP_PHOTOS_AFTER_ENCODING
)

logger = logging.getLogger(__name__)


class FaceRecognitionProcessor:
    """Clase para procesar reconocimiento facial"""

    def __init__(self) -> None:
        self.known_encodings: List[np.ndarray] = []
        self.known_ids: List[int] = []
        self.known_names: List[str] = []
        self.encodings_loaded: bool = False

        # Cargar encodings si existe el archivo
        if os.path.exists(ENCODINGS_FILE):
            self.cargar_encodings()
        else:
            logger.warning(f"Archivo de encodings no encontrado: {ENCODINGS_FILE}")

    def cargar_encodings(self) -> None:
        """
        Carga los encodings pre-calculados desde archivo pickle

        Raises:
            Exception: Si hay un error al cargar el archivo de encodings
        """
        try:
            with open(ENCODINGS_FILE, 'rb') as f:
                data = pickle.load(f)

            self.known_encodings = data['encodings']
            self.known_ids = data['ids']
            self.known_names = data['names']
            self.encodings_loaded = True

            logger.info(f"Encodings cargados exitosamente: {len(self.known_encodings)} rostros")

        except Exception as e:
            logger.error(f"Error al cargar encodings desde {ENCODINGS_FILE}: {e}")
            self.encodings_loaded = False

    def generar_encodings_desde_fotos(self, estudiantes_db: List[Dict[str, Any]]) -> None:
        """
        Genera encodings desde las fotos en la carpeta y los guarda

        Args:
            estudiantes_db: Lista de estudiantes desde la BD con formato:
                [{'id_estudiante': int, 'nombre_completo': str, 'path_foto_referencia': str}, ...]

        Note:
            Los encodings se guardan automáticamente en ENCODINGS_FILE.
            Si KEEP_PHOTOS_AFTER_ENCODING=false, las fotos se eliminan después de generar encodings.
        """
        logger.info("Generando encodings desde fotos de estudiantes...")

        encodings: List[np.ndarray] = []
        ids: List[int] = []
        names: List[str] = []
        fotos_procesadas: List[str] = []  # Track de fotos exitosamente procesadas

        for estudiante in estudiantes_db:
            id_estudiante = estudiante['id_estudiante']
            nombre = estudiante['nombre_completo']
            path_foto = estudiante['path_foto_referencia']

            # Construir ruta completa
            full_path = os.path.join(str(PHOTOS_DIR), path_foto)

            if not os.path.exists(full_path):
                logger.warning(f"Foto no encontrada: {full_path}")
                continue

            try:
                # Cargar imagen
                image = face_recognition.load_image_file(full_path)

                # Generar encoding
                face_encodings = face_recognition.face_encodings(image)

                if len(face_encodings) > 0:
                    encodings.append(face_encodings[0])
                    ids.append(id_estudiante)
                    names.append(nombre)
                    fotos_procesadas.append(full_path)  # Track para eliminar después
                    logger.info(f"Encoding generado exitosamente: {nombre}")
                else:
                    logger.warning(
                        f"No se detectó rostro en la imagen: {path_foto}. "
                        f"Verifica que la foto contenga un rostro visible."
                    )

            except Exception as e:
                logger.error(f"Error procesando foto {path_foto}: {e}")

        # Guardar encodings
        if len(encodings) > 0:
            data = {
                'encodings': encodings,
                'ids': ids,
                'names': names
            }

            # Crear directorio si no existe
            os.makedirs(os.path.dirname(ENCODINGS_FILE), exist_ok=True)

            with open(ENCODINGS_FILE, 'wb') as f:
                pickle.dump(data, f)

            self.known_encodings = encodings
            self.known_ids = ids
            self.known_names = names
            self.encodings_loaded = True

            logger.info(f"Encodings guardados exitosamente: {len(encodings)} rostros en {ENCODINGS_FILE}")

            # Eliminar fotos si está configurado (cumplimiento Ley 19.628)
            if not KEEP_PHOTOS_AFTER_ENCODING:
                logger.info("Eliminando fotos originales (KEEP_PHOTOS_AFTER_ENCODING=false)...")
                fotos_eliminadas = 0
                for foto_path in fotos_procesadas:
                    try:
                        os.remove(foto_path)
                        fotos_eliminadas += 1
                        logger.debug(f"Foto eliminada: {foto_path}")
                    except Exception as e:
                        logger.error(f"Error al eliminar foto {foto_path}: {e}")

                logger.info(
                    f"Fotos eliminadas: {fotos_eliminadas}/{len(fotos_procesadas)} "
                    f"(cumplimiento principio de minimización de datos - Ley 19.628)"
                )
            else:
                logger.info(
                    f"Fotos conservadas (KEEP_PHOTOS_AFTER_ENCODING=true). "
                    f"IMPORTANTE: Requiere consentimiento explícito de estudiantes."
                )
        else:
            logger.error(
                "No se generó ningún encoding. Verifica que las fotos contengan rostros visibles."
            )

    def procesar_frame(self, image_array: np.ndarray) -> Dict[str, Any]:
        """
        Procesa un frame y busca rostros conocidos

        Args:
            image_array: Frame en formato numpy array (RGB)

        Returns:
            Dict con resultado del procesamiento:
            {
                'faces_found': int,
                'matches': [{'id': int, 'name': str, 'location': tuple, 'confidence': float}],
                'error': str (opcional, solo si hay error)
            }

        Example:
            >>> processor.procesar_frame(image_array)
            {'faces_found': 1, 'matches': [{'id': 1, 'name': 'Juan Pérez', ...}]}
        """
        if not self.encodings_loaded:
            return {
                'faces_found': 0,
                'matches': [],
                'error': 'Encodings no cargados. Ejecuta primero /api/recargar-encodings'
            }

        try:
            # Detectar ubicaciones de rostros
            face_locations = face_recognition.face_locations(
                image_array,
                model=FACE_DETECTION_MODEL
            )

            if len(face_locations) == 0:
                return {
                    'faces_found': 0,
                    'matches': []
                }

            # Generar encodings para los rostros detectados
            face_encodings = face_recognition.face_encodings(
                image_array,
                face_locations
            )

            matches_result: List[Dict[str, Any]] = []

            # Comparar cada rostro detectado con los conocidos
            for face_encoding, face_location in zip(face_encodings, face_locations):
                # Comparar con todos los rostros conocidos
                matches = face_recognition.compare_faces(
                    self.known_encodings,
                    face_encoding,
                    tolerance=FACE_TOLERANCE
                )

                # Calcular distancias para encontrar la mejor coincidencia
                face_distances = face_recognition.face_distance(
                    self.known_encodings,
                    face_encoding
                )

                if True in matches:
                    # Encontrar la mejor coincidencia (menor distancia)
                    best_match_index = np.argmin(face_distances)

                    if matches[best_match_index]:
                        id_estudiante = self.known_ids[best_match_index]
                        nombre = self.known_names[best_match_index]
                        confidence = 1 - face_distances[best_match_index]

                        matches_result.append({
                            'id': id_estudiante,
                            'name': nombre,
                            'location': face_location,
                            'confidence': float(confidence)
                        })

            return {
                'faces_found': len(face_locations),
                'matches': matches_result
            }

        except Exception as e:
            logger.error(f"Error al procesar frame de reconocimiento facial: {e}")
            return {
                'faces_found': 0,
                'matches': [],
                'error': str(e)
            }

    def decode_image_from_base64(self, base64_string: str) -> Optional[np.ndarray]:
        """
        Decodifica una imagen base64 a numpy array

        Args:
            base64_string: Imagen codificada en base64

        Returns:
            numpy array en formato RGB o None si falla la decodificación

        Example:
            >>> img_array = processor.decode_image_from_base64(base64_str)
            >>> type(img_array)
            <class 'numpy.ndarray'>
        """
        try:
            # Decodificar base64
            img_data = base64.b64decode(base64_string)

            # Convertir a PIL Image
            img = Image.open(io.BytesIO(img_data))

            # Convertir a RGB si es necesario
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Convertir a numpy array
            img_array = np.array(img)

            return img_array

        except Exception as e:
            logger.error(f"Error al decodificar imagen desde base64: {e}")
            return None


# Instancia global
face_recognition_processor = FaceRecognitionProcessor()
