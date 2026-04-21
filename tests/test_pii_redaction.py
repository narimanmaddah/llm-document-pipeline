import pytest
from pipeline.pii.detector import PIIDetector
from pipeline.pii.redactor import PIIRedactor


def test_email_detection():
    detector = PIIDetector()
    text = "Contact me at john.doe@example.com"
    detections = detector.detect(text, ["EMAIL"])
    assert len(detections) == 1
    assert detections[0][0] == "EMAIL"
    assert detections[0][1] == "john.doe@example.com"


def test_phone_detection():
    detector = PIIDetector()
    text = "Call me at (555) 123-4567"
    detections = detector.detect(text, ["PHONE"])
    assert len(detections) >= 1
    assert detections[0][0] == "PHONE"


def test_iban_detection():
    detector = PIIDetector()
    text = "My IBAN is DE89370400440532013000"
    detections = detector.detect(text, ["IBAN"])
    assert len(detections) == 1
    assert detections[0][0] == "IBAN"


def test_redaction():
    redactor = PIIRedactor()
    text = "Contact john@example.com or call (555) 123-4567"
    redacted, metadata = redactor.redact(text, ["EMAIL", "PHONE"])
    assert metadata["pii_detected"] is True
    assert "[REDACTED]" in redacted
    assert "john@example.com" not in redacted


def test_no_pii():
    detector = PIIDetector()
    text = "This is just plain text with no personal info"
    detections = detector.detect(text, ["EMAIL", "PHONE", "IBAN"])
    assert len(detections) == 0
