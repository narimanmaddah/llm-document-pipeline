import re
from typing import List, Tuple, Dict


class PIIDetector:
    """Simple regex-based PII detection."""

    PATTERNS = {
        "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "PHONE": r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b",
        "IBAN": r"\b[A-Z]{2}[0-9]{2}[A-Z0-9]{1,30}\b",
        "TAX_ID": r"\b\d{2}-\d{7}\b",  # US format
        "PERSON": r"\b(?:Mr\.|Ms\.|Dr\.|Prof\.|Mrs\.)\s+[A-Z][a-z]+\b",
    }

    def detect(self, text: str, entities_to_detect: List[str]) -> List[Tuple[str, str, int, int]]:
        """
        Detect PII in text.
        Returns: [(entity_type, matched_text, start_pos, end_pos), ...]
        """
        results = []
        for entity_type in entities_to_detect:
            if entity_type not in self.PATTERNS:
                continue
            pattern = self.PATTERNS[entity_type]
            for match in re.finditer(pattern, text):
                results.append((entity_type, match.group(), match.start(), match.end()))
        return results

    def has_pii(self, text: str, entities_to_detect: List[str]) -> bool:
        """Check if text contains any PII."""
        return len(self.detect(text, entities_to_detect)) > 0
