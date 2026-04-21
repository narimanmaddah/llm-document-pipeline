from typing import Dict, Any, List


class ConfidenceScorer:
    """Simple heuristic confidence scorer for extracted fields."""

    # Field patterns for pattern-matching confidence boost
    PATTERNS = {
        "invoice_number": [r"INV-\d+", r"INV\d+", r"#\d{6,}"],
        "total_amount": [r"\$[\d,]+\.\d{2}", r"€[\d,]+\.\d{2}"],
        "issue_date": [r"\d{4}-\d{2}-\d{2}", r"\d{2}/\d{2}/\d{4}"],
    }

    def score_field(self, field_name: str, field_value: Any) -> float:
        """Score confidence for a single field (0-1)."""
        if field_value is None:
            return 0.0

        # If null/empty, confidence is 0
        if isinstance(field_value, str) and not field_value.strip():
            return 0.0

        # Base confidence for non-null values
        confidence = 0.7

        # Boost for fields matching expected patterns
        if field_name in self.PATTERNS:
            import re

            value_str = str(field_value)
            for pattern in self.PATTERNS[field_name]:
                if re.search(pattern, value_str):
                    confidence = 0.95
                    break

        return confidence

    def score_document(self, extracted_fields: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Score all fields in extracted document."""
        scored = {}
        for field_name, field_value in extracted_fields.items():
            confidence = self.score_field(field_name, field_value)
            scored[field_name] = {"value": field_value, "confidence": round(confidence, 2)}

        return scored
