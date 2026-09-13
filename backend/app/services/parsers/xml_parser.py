import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
from app.services.parsers.base import BaseParser, ParsedEvent

# Prohibit external entity declarations or entity expansion (XXE protection)
XXE_PROHIBITED_RE = re.compile(r"<!DOCTYPE|<!ENTITY", re.IGNORECASE)


class XmlParser(BaseParser):
    parser_id = "xml_generic"
    parser_version = "1.0.0"
    supported_formats = ["xml"]

    def can_parse(self, payload: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        if not payload:
            return False
        p = payload.strip()
        return p.startswith("<?xml") or (p.startswith("<") and p.endswith(">"))

    def parse(self, payload: str, metadata: Optional[Dict[str, Any]] = None) -> ParsedEvent:
        warnings: List[str] = []
        errors: List[str] = []
        extracted: Dict[str, Any] = {}
        custom: Dict[str, Any] = {}

        text = payload.strip()

        # XXE Protection check
        if XXE_PROHIBITED_RE.search(text):
            errors.append("Security rejection: Payload contains prohibited <!DOCTYPE or <!ENTITY declarations (XXE protection).")
            return ParsedEvent(
                extracted_fields={},
                parser_id=self.parser_id,
                parser_version=self.parser_version,
                source_format="xml",
                warnings=warnings,
                errors=errors,
                confidence=0.0,
                custom_fields={"security_event": "XXE_ATTEMPT_BLOCKED"}
            )

        try:
            parser = ET.XMLParser()
            root = ET.fromstring(text, parser=parser)
        except Exception as exc:
            errors.append(f"Malformed XML: {str(exc)}")
            return ParsedEvent(
                extracted_fields={},
                parser_id=self.parser_id,
                parser_version=self.parser_version,
                source_format="xml",
                warnings=warnings,
                errors=errors,
                confidence=0.0,
                custom_fields={"raw_payload": text}
            )

        # Recursively convert element tree into dictionary
        extracted["xml_root_tag"] = root.tag
        self._flatten_element(root, extracted, custom)

        return ParsedEvent(
            extracted_fields=extracted,
            parser_id=self.parser_id,
            parser_version=self.parser_version,
            source_format="xml",
            warnings=warnings,
            errors=errors,
            confidence=0.95,
            custom_fields=custom
        )

    def _flatten_element(self, element: ET.Element, extracted: Dict[str, Any], custom: Dict[str, Any]) -> None:
        """Extracts attributes and child elements into extracted and custom fields."""
        # Extract XML attributes
        for attr_k, attr_v in element.attrib.items():
            extracted[f"{element.tag}_{attr_k}"] = attr_v

        # Extract child elements
        children = list(element)
        if not children and element.text and element.text.strip():
            extracted[element.tag] = element.text.strip()
        else:
            for child in children:
                if len(list(child)) == 0 and child.text and child.text.strip():
                    extracted[child.tag] = child.text.strip()
                    # Also collect attributes of child
                    for ck, cv in child.attrib.items():
                        extracted[f"{child.tag}_{ck}"] = cv
                else:
                    # Nested element -> store in custom_fields
                    custom[child.tag] = self._element_to_dict(child)

    def _element_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        result: Dict[str, Any] = dict(element.attrib)
        if element.text and element.text.strip():
            result["text"] = element.text.strip()
        for child in element:
            child_dict = self._element_to_dict(child)
            if child.tag in result:
                if isinstance(result[child.tag], list):
                    result[child.tag].append(child_dict)
                else:
                    result[child.tag] = [result[child.tag], child_dict]
            else:
                result[child.tag] = child_dict
        return result
