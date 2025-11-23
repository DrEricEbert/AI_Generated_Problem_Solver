"""
Kamera-Plugin - VOLLSTÄNDIG MIT PARAMETERN
"""

import random
import time
import logging
import io
from core.plugin_manager import MeasurementPlugin

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL/Pillow nicht verfuegbar - Kamera-Plugin eingeschraenkt")


class CameraPlugin(MeasurementPlugin):
    """Simulierte Kamera mit Parametern"""

    def __init__(self):
        super().__init__()
        self.name = "CameraPlugin"
        self.version = "2.0"
        self.description = "Simulierte Kamera fuer Bildaufnahme und -analyse mit Parametern"

        # Parameter-Definitionen
        self._parameter_definitions = {
            'resolution_width': {
                'type': 'int',
                'default': 640,
                'min': 320,
                'max': 1920,
                'description': 'Bildbreite in Pixel'
            },
            'resolution_height': {
                'type': 'int',
                'default': 480,
                'min': 240,
                'max': 1080,
                'description': 'Bildhoehe in Pixel'
            },
            'default_exposure': {
                'type': 'float',
                'default': 100.0,
                'min': 1.0,
                'max': 1000.0,
                'increment': 1.0,
                'unit': 'ms',
                'description': 'Standard-Belichtungszeit'
            },
            'default_gain': {
                'type': 'float',
                'default': 1.0,
                'min': 0.1,
                'max': 10.0,
                'increment': 0.1,
                'description': 'Standard-Verstaerkung'
            },
            'enable_overlay': {
                'type': 'bool',
                'default': True,
                'description': 'Text-Overlay auf Bild anzeigen'
            },
            'image_format': {
                'type': 'choice',
                'default': 'PNG',
                'choices': ['PNG', 'JPEG', 'BMP'],
                'description': 'Bildformat'
            },
            'jpeg_quality': {
                'type': 'int',
                'default': 90,
                'min': 10,
                'max': 100,
                'description': 'JPEG-Qualitaet (nur fuer JPEG)'
            },
            'noise_level': {
                'type': 'int',
                'default': 5,
                'min': 0,
                'max': 50,
                'description': 'Bild-Rauschpegel'
            }
        }

        # Setze Standardwerte
        for param_name, param_def in self._parameter_definitions.items():
            self.parameters[param_name] = param_def['default']

        self.exposure_time = 100
        self.gain = 1.0
        self.connected = False

    def initialize(self):
        """Initialisiere Kamera"""
        try:
            logger.info(f"{self.name}: Initialisierung gestartet")

            width = self.get_parameter_value('resolution_width', 640)
            height = self.get_parameter_value('resolution_height', 480)
            logger.info(f"{self.name}: Aufloesung: {width}x{height}")

            if not PIL_AVAILABLE:
                logger.warning(f"{self.name}: PIL nicht verfuegbar - Bildgenerierung eingeschraenkt")

            time.sleep(0.3)
            self.connected = True
            self.is_initialized = True

            logger.info(f"{self.name}: Erfolgreich initialisiert")
            return True

        except Exception as e:
            logger.error(f"{self.name}: Initialisierung fehlgeschlagen: {e}")
            return False

    def cleanup(self):
        """Cleanup"""
        logger.info(f"{self.name}: Cleanup")
        self.connected = False
        self.is_initialized = False

    def set_parameters(self, parameters: dict):
        """Setze Kamera-Parameter"""
        if 'exposure' in parameters:
            self.exposure_time = max(1, min(1000, parameters['exposure']))
            logger.info(f"{self.name}: Belichtungszeit gesetzt auf {self.exposure_time}ms")
        else:
            self.exposure_time = self.get_parameter_value('default_exposure', 100.0)

        if 'gain' in parameters:
            self.gain = max(0.1, min(10.0, parameters['gain']))
            logger.info(f"{self.name}: Verstaerkung gesetzt auf {self.gain}")
        else:
            self.gain = self.get_parameter_value('default_gain', 1.0)

    def measure(self) -> dict:
        """Führe Bildaufnahme durch"""
        if not self.is_initialized:
            raise RuntimeError(f"{self.name}: Kamera nicht initialisiert")

        # Simuliere Belichtungszeit
        time.sleep(self.exposure_time / 1000.0)

        # Generiere Testbild
        image_data = self._generate_test_image()

        # Analysiere Bild
        analysis = self._analyze_image(image_data)

        width = self.get_parameter_value('resolution_width', 640)
        height = self.get_parameter_value('resolution_height', 480)
        image_format = self.get_parameter_value('image_format', 'PNG')

        result = {
            'image': image_data,
            'mean_intensity': analysis['mean_intensity'],
            'std_intensity': analysis['std_intensity'],
            'width': width,
            'height': height,
            'exposure_time': self.exposure_time,
            'gain': self.gain,
            'image_format': image_format,
            'image_size_bytes': len(image_data) if isinstance(image_data, bytes) else 0,
            'unit_info': {
                'mean_intensity': '',
                'std_intensity': '',
                'width': 'px',
                'height': 'px',
                'exposure_time': 'ms',
                'gain': '',
                'image_format': '',
                'image_size_bytes': 'Bytes'
            }
        }

        logger.debug(f"{self.name}: Bild aufgenommen ({width}x{height}, {image_format})")
        return result

    def _generate_test_image(self):
        """Generiere Testbild"""
        width = self.get_parameter_value('resolution_width', 640)
        height = self.get_parameter_value('resolution_height', 480)
        enable_overlay = self.get_parameter_value('enable_overlay', True)
        noise_level = self.get_parameter_value('noise_level', 5)
        image_format = self.get_parameter_value('image_format', 'PNG')

        if PIL_AVAILABLE:
            # Erstelle Testbild
            img = Image.new('RGB', (width, height), color=(128, 128, 128))
            draw = ImageDraw.Draw(img)

            # Gradient
            for y in range(height):
                intensity = int(255 * y / height)
                intensity = max(0, min(255, intensity + random.randint(-noise_level, noise_level)))
                draw.line([(0, y), (width//3, y)], fill=(intensity, intensity, intensity))

            # Rechtecke
            draw.rectangle([50, 50, 150, 150], outline=(255, 0, 0), width=3)
            draw.rectangle([200, 100, 300, 200], outline=(0, 255, 0), width=3)

            # Text-Overlay wenn aktiviert
            if enable_overlay:
                try:
                    text = f"Exp: {self.exposure_time}ms, Gain: {self.gain}"
                    draw.text((10, 10), text, fill=(255, 255, 0))
                except:
                    pass

            # Konvertiere zu Bytes im gewählten Format
            buf = io.BytesIO()

            if image_format == 'JPEG':
                quality = self.get_parameter_value('jpeg_quality', 90)
                img.save(buf, format='JPEG', quality=quality)
            elif image_format == 'BMP':
                img.save(buf, format='BMP')
            else:  # PNG
                img.save(buf, format='PNG')

            return buf.getvalue()
        else:
            return b'SIMULATED_IMAGE_DATA'

    def _analyze_image(self, image_data):
        """Analysiere Bild"""
        if PIL_AVAILABLE and len(image_data) > 100:
            try:
                img = Image.open(io.BytesIO(image_data))
                gray = img.convert('L')
                pixels = list(gray.getdata())

                mean = sum(pixels) / len(pixels)
                variance = sum((x - mean) ** 2 for x in pixels) / len(pixels)
                std = variance ** 0.5

                return {
                    'mean_intensity': round(mean, 2),
                    'std_intensity': round(std, 2)
                }
            except:
                pass

        # Fallback
        noise_level = self.get_parameter_value('noise_level', 5)
        return {
            'mean_intensity': 128.0 + random.gauss(0, noise_level),
            'std_intensity': 30.0 + random.gauss(0, 2)
        }

    def get_units(self) -> dict:
        return {
            'mean_intensity': '',
            'std_intensity': '',
            'width': 'px',
            'height': 'px',
            'exposure_time': 'ms',
            'gain': '',
            'image_format': '',
            'image_size_bytes': 'Bytes'
        }
