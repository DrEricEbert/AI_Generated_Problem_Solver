"""
Beispiel-Plugin: Bildverarbeitung
Analysiert Kamerabilder
"""

import logging
import io
from core.plugin_manager import ProcessingPlugin

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageFilter, ImageStat
    import numpy as np
    IMAGE_PROCESSING_AVAILABLE = True
except ImportError:
    IMAGE_PROCESSING_AVAILABLE = False
    logger.warning("PIL/NumPy nicht verfügbar - Bildverarbeitung nicht möglich")


class ImageProcessor(ProcessingPlugin):
    """Bildverarbeitungs-Plugin"""

    def __init__(self):
        super().__init__()
        self.name = "ImageProcessor"
        self.version = "1.0"
        self.description = "Analysiert und verarbeitet Kamerabilder"

    def initialize(self):
        """Initialisiere"""
        logger.info(f"{self.name}: Initialisierung")
        self.is_initialized = True
        return True

    def cleanup(self):
        """Cleanup"""
        self.is_initialized = False

    def get_required_inputs(self) -> list:
        return ['image']

    def process(self, data: dict) -> dict:
        """Verarbeite Bilddaten"""
        if not IMAGE_PROCESSING_AVAILABLE:
            logger.warning(f"{self.name}: Bildverarbeitung nicht verfügbar")
            return {'error': 'PIL/NumPy not available'}

        # Suche Bilddaten
        image_data = None
        for plugin_results in data.values():
            if isinstance(plugin_results, dict) and 'image' in plugin_results:
                image_data = plugin_results['image']
                break

        if not image_data or not isinstance(image_data, bytes):
            logger.warning(f"{self.name}: Keine Bilddaten gefunden")
            return {}

        try:
            # Lade Bild
            img = Image.open(io.BytesIO(image_data))

            # Basis-Analyse
            result = {
                'image_width': img.size[0],
                'image_height': img.size[1],
                'image_mode': img.mode,
                'image_format': img.format if img.format else 'unknown'
            }

            # Konvertiere zu Graustufen für Analyse
            gray = img.convert('L')

            # Statistiken
            stat = ImageStat.Stat(gray)
            result['brightness_mean'] = round(stat.mean[0], 2)
            result['brightness_std'] = round(stat.stddev[0], 2)
            result['brightness_median'] = round(stat.median[0], 2)

            # Histogramm-Analyse
            histogram = gray.histogram()

            # Finde dominanten Intensitätsbereich
            max_bin = histogram.index(max(histogram))
            result['dominant_intensity'] = max_bin

            # Kontrast (Differenz zwischen 95% und 5% Percentile)
            pixels = list(gray.getdata())
            sorted_pixels = sorted(pixels)
            n = len(sorted_pixels)
            p5 = sorted_pixels[int(n * 0.05)]
            p95 = sorted_pixels[int(n * 0.95)]
            result['contrast_range'] = p95 - p5

            # Kantenerkennung
            edges = gray.filter(ImageFilter.FIND_EDGES)
            edge_stat = ImageStat.Stat(edges)
            result['edge_strength'] = round(edge_stat.mean[0], 2)

            # Schärfe-Schätzung (Varianz des Laplace-Filters)
            laplacian = gray.filter(ImageFilter.Kernel((3, 3),
                [-1, -1, -1, -1, 8, -1, -1, -1, -1], 1, 0))
            lap_array = np.array(laplacian)
            result['sharpness'] = round(float(np.var(lap_array)), 2)

            # Blob-Detektion (vereinfacht: Anzahl zusammenhängender Bereiche)
            threshold = gray.point(lambda x: 255 if x > 128 else 0)
            result['binary_white_ratio'] = round(
                sum(1 for p in threshold.getdata() if p > 0) / len(list(threshold.getdata())),
                4
            )

            logger.info(f"{self.name}: Bild analysiert ({img.size[0]}x{img.size[1]})")
            return result

        except Exception as e:
            logger.error(f"{self.name}: Fehler bei Bildverarbeitung: {e}")
            return {'error': str(e)}


class ImageQualityChecker(ProcessingPlugin):
    """Prüft Bildqualität"""

    def __init__(self):
        super().__init__()
        self.name = "ImageQualityChecker"
        self.version = "1.0"
        self.description = "Prüft Bildqualität und erkennt Probleme"

    def initialize(self):
        logger.info(f"{self.name}: Initialisierung")
        self.is_initialized = True
        return True

    def cleanup(self):
        self.is_initialized = False

    def get_required_inputs(self) -> list:
        return ['image']

    def process(self, data: dict) -> dict:
        """Prüfe Bildqualität"""
        if not IMAGE_PROCESSING_AVAILABLE:
            return {'error': 'PIL/NumPy not available'}

        # Suche Bilddaten
        image_data = None
        for plugin_results in data.values():
            if isinstance(plugin_results, dict) and 'image' in plugin_results:
                image_data = plugin_results['image']
                break

        if not image_data:
            return {}

        try:
            img = Image.open(io.BytesIO(image_data))
            gray = img.convert('L')

            stat = ImageStat.Stat(gray)
            mean_brightness = stat.mean[0]
            std_brightness = stat.stddev[0]

            result = {}

            # Überbelichtung
            result['overexposed'] = 1 if mean_brightness > 240 else 0

            # Unterbelichtung
            result['underexposed'] = 1 if mean_brightness < 20 else 0

            # Niedriger Kontrast
            result['low_contrast'] = 1 if std_brightness < 20 else 0

            # Qualitätsscore (0-100)
            quality_score = 100
            if result['overexposed']:
                quality_score -= 30
            if result['underexposed']:
                quality_score -= 30
            if result['low_contrast']:
                quality_score -= 20

            # Bonus für guten Kontrast
            if std_brightness > 40:
                quality_score = min(100, quality_score + 10)

            result['quality_score'] = max(0, quality_score)
            result['quality_rating'] = (
                'excellent' if quality_score >= 90 else
                'good' if quality_score >= 70 else
                'fair' if quality_score >= 50 else
                'poor'
            )

            return result

        except Exception as e:
            logger.error(f"{self.name}: Fehler: {e}")
            return {'error': str(e)}
