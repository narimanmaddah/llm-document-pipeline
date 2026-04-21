from typing import Dict, Any


class ReviewRouter:
    """Route documents to human review based on confidence and quality scores."""

    def __init__(self, field_review_threshold: float = 0.80, document_auto_approve: float = 0.90):
        self.field_review_threshold = field_review_threshold
        self.document_auto_approve = document_auto_approve

    def should_route_for_review(
        self, scored_fields: Dict[str, Dict[str, Any]], quality_score: float, pii_detected: bool
    ) -> bool:
        """Determine if document needs human review."""
        # Route if quality is too low
        if quality_score < 0.70:
            return True

        # Route if any high-risk fields are low confidence
        low_confidence_fields = [f for f, data in scored_fields.items() if data.get("confidence", 0) < self.field_review_threshold]

        if low_confidence_fields:
            return True

        # Route if PII was detected (human should verify redaction)
        if pii_detected:
            return True

        return False

    def get_confidence_summary(self, scored_fields: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Get confidence statistics."""
        confidences = [data.get("confidence", 0) for data in scored_fields.values()]
        if not confidences:
            return {"avg": 0, "min": 0, "max": 0}

        return {
            "avg": round(sum(confidences) / len(confidences), 2),
            "min": round(min(confidences), 2),
            "max": round(max(confidences), 2),
        }
