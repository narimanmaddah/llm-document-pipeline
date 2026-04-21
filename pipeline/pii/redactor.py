import re
import json
import os
from datetime import datetime
from typing import Tuple, List, Dict, Set
from .detector import PIIDetector


class PIIRedactor:
    """Redact PII from text and maintain audit log."""

    REDACTION_MARKER = "[REDACTED]"

    def __init__(self, audit_log_path: str = "logs/pii_audit.jsonl"):
        self.detector = PIIDetector()
        self.audit_log_path = audit_log_path
        os.makedirs(os.path.dirname(audit_log_path) or ".", exist_ok=True)

    def redact(self, text: str, entities_to_detect: List[str]) -> Tuple[str, Dict]:
        """Redact PII and return redacted text + metadata about what was found."""
        detections = self.detector.detect(text, entities_to_detect)
        pii_found = list(set(d[0] for d in detections))

        redacted_text = text
        for entity_type, matched_text, start_pos, end_pos in sorted(detections, key=lambda x: x[2], reverse=True):
            redacted_text = redacted_text[:start_pos] + self.REDACTION_MARKER + redacted_text[end_pos:]

        metadata = {
            "timestamp": datetime.utcnow().isoformat(),
            "pii_detected": bool(pii_found),
            "pii_types": pii_found,
            "redaction_count": len(detections),
            "redaction_mode": "replace",
        }

        if pii_found:
            self._log_audit(metadata, detections)

        return redacted_text, metadata

    def _log_audit(self, metadata: Dict, detections: List[Tuple]):
        """Log to audit trail without recording actual PII values."""
        audit_entry = {
            "timestamp": metadata["timestamp"],
            "pii_detected": True,
            "entity_types_found": list(set(d[0] for d in detections)),
            "count": len(detections),
        }
        with open(self.audit_log_path, "a") as f:
            f.write(json.dumps(audit_entry) + "\n")
