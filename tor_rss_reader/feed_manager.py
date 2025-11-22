"""
RSS Feed Manager
"""

import feedparser
from typing import List, Dict, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class FeedManager:
    """Verwaltet RSS Feed-Operationen"""

    def __init__(self, tor_handler):
        self.tor_handler = tor_handler

    def fetch_feed(self, feed_url: str) -> List[Dict[str, Any]]:
        """Lädt einen RSS Feed"""
        try:
            logger.info(f"Lade Feed: {feed_url}")

            # Feed über TOR laden
            response = self.tor_handler.get(feed_url, timeout=30)

            # Feed parsen
            feed = feedparser.parse(response.content)

            if feed.bozo:
                logger.warning(f"Feed-Parsing-Warnung: {feed.bozo_exception}")

            # Einträge extrahieren
            entries = []
            for entry in feed.entries:
                entry_data = {
                    'title': entry.get('title', 'Kein Titel'),
                    'link': entry.get('link', ''),
                    'summary': self._clean_html(entry.get('summary', entry.get('description', ''))),
                    'published': self._format_date(entry.get('published', entry.get('updated', ''))),
                    'author': entry.get('author', ''),
                }
                entries.append(entry_data)

            logger.info(f"Feed geladen: {len(entries)} Einträge")
            return entries

        except Exception as e:
            logger.error(f"Fehler beim Laden des Feeds {feed_url}: {e}")
            raise Exception(f"Feed konnte nicht geladen werden: {str(e)}")

    def _clean_html(self, text: str) -> str:
        """Entfernt HTML-Tags aus Text"""
        import re
        # Einfache HTML-Tag-Entfernung
        text = re.sub('<[^<]+?>', '', text)
        # Mehrfache Leerzeichen entfernen
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _format_date(self, date_str: str) -> str:
        """Formatiert Datum-String"""
        if not date_str:
            return ''

        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(date_str)
            return dt.strftime('%d.%m.%Y %H:%M')
        except:
            return date_str
