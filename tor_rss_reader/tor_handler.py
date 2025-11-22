"""
TOR-Handler für sichere Verbindungen
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import socks
import socket
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class TorHandler:
    """Verwaltet TOR-Verbindungen"""

    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.session = None
        self._setup_session()

    def _setup_session(self):
        """Richtet die Requests-Session mit TOR ein"""
        self.session = requests.Session()

        # Retry-Strategie
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # TOR Proxy konfigurieren
        proxy_host = self.config_manager.get('tor_proxy_host', '127.0.0.1')
        proxy_port = self.config_manager.get('tor_proxy_port', 9050)

        self.session.proxies = {
            'http': f'socks5h://{proxy_host}:{proxy_port}',
            'https': f'socks5h://{proxy_host}:{proxy_port}'
        }

        # User-Agent
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0'
        })

        logger.info(f"TOR-Session konfiguriert: {proxy_host}:{proxy_port}")

    def get(self, url: str, timeout: int = 30) -> requests.Response:
        """Führt einen GET-Request über TOR aus"""
        try:
            # Versuche zuerst mit TOR
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response
        except Exception as e:
            logger.warning(f"TOR-Request fehlgeschlagen, versuche ohne TOR: {e}")
            # Fallback ohne TOR
            try:
                response = requests.get(url, timeout=timeout)
                response.raise_for_status()
                return response
            except Exception as e2:
                logger.error(f"Auch Request ohne TOR fehlgeschlagen: {e2}")
                raise

    def check_tor_connection(self) -> Tuple[bool, Optional[str]]:
        """Prüft die TOR-Verbindung"""
        try:
            # Anfrage an check.torproject.org
            response = self.session.get(
                'https://check.torproject.org/api/ip',
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                is_tor = data.get('IsTor', False)
                ip = data.get('IP', 'Unbekannt')

                if is_tor:
                    logger.info(f"TOR-Verbindung aktiv: {ip}")
                    return True, ip
                else:
                    logger.warning(f"Keine TOR-Verbindung: {ip}")
                    return False, ip
            else:
                logger.error("TOR-Check fehlgeschlagen")
                return False, None

        except Exception as e:
            logger.error(f"Fehler beim TOR-Check: {e}")
            return False, None

    def get_new_identity(self):
        """Fordert eine neue TOR-Identität an (benötigt Controller-Zugriff)"""
        # Hier könnte die stem-Bibliothek verwendet werden
        # für erweiterte TOR-Kontrolle
        pass
