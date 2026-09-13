from typing import Dict, List, Optional
from app.services.parsers.base import BaseParser
from app.services.parsers.syslog import SyslogParser
from app.services.parsers.json_parser import JsonParser
from app.services.parsers.csv_parser import CsvParser
from app.services.parsers.cef import CefParser
from app.services.parsers.leef import LeefParser
from app.services.parsers.xml_parser import XmlParser


class ParserRegistry:
    """
    Registry for modular parser plugins.
    Decouples parsing engines and provides automatic parser selection.
    """

    def __init__(self):
        self._parsers: Dict[str, BaseParser] = {}
        self._format_map: Dict[str, List[BaseParser]] = {}
        self._register_builtins()

    def _register_builtins(self):
        builtins = [
            CefParser(),
            LeefParser(),
            JsonParser(),
            XmlParser(),
            SyslogParser(),
            CsvParser(),
        ]
        for parser in builtins:
            self.register_parser(parser)

    def register_parser(self, parser: BaseParser) -> None:
        """Registers a parser plugin."""
        self._parsers[parser.parser_id] = parser
        for fmt in parser.supported_formats:
            fmt_lower = fmt.lower()
            if fmt_lower not in self._format_map:
                self._format_map[fmt_lower] = []
            if parser not in self._format_map[fmt_lower]:
                self._format_map[fmt_lower].append(parser)

    def get_parser(self, parser_id: str) -> Optional[BaseParser]:
        """Look up parser by unique ID."""
        return self._parsers.get(parser_id)

    def list_parsers(self) -> List[BaseParser]:
        """Returns all registered parsers."""
        return list(self._parsers.values())

    def select_parser(
        self,
        detected_format: str,
        payload: str,
        parser_id_hint: Optional[str] = None
    ) -> Optional[BaseParser]:
        """
        Selects the best parser for an event based on format or explicit hint.
        """
        if parser_id_hint and parser_id_hint in self._parsers:
            return self._parsers[parser_id_hint]

        candidates = self._format_map.get(detected_format.lower(), [])
        for candidate in candidates:
            if candidate.can_parse(payload):
                return candidate

        # Fallback check across all parsers
        for candidate in self._parsers.values():
            if candidate.can_parse(payload):
                return candidate

        return None


# Global parser registry instance
default_parser_registry = ParserRegistry()
