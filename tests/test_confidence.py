import pytest
from pipeline.extraction.confidence import ConfidenceScorer


def test_confidence_null_field():
    scorer = ConfidenceScorer()
    confidence = scorer.score_field("invoice_number", None)
    assert confidence == 0.0


def test_confidence_empty_string():
    scorer = ConfidenceScorer()
    confidence = scorer.score_field("invoice_number", "")
    assert confidence == 0.0


def test_confidence_invoice_pattern():
    scorer = ConfidenceScorer()
    confidence = scorer.score_field("invoice_number", "INV-123456")
    assert confidence >= 0.9


def test_confidence_amount_pattern():
    scorer = ConfidenceScorer()
    confidence = scorer.score_field("total_amount", "$1,234.56")
    assert confidence >= 0.9


def test_confidence_date_pattern():
    scorer = ConfidenceScorer()
    confidence = scorer.score_field("issue_date", "2024-03-15")
    assert confidence >= 0.9


def test_confidence_generic_field():
    scorer = ConfidenceScorer()
    confidence = scorer.score_field("vendor_name", "Acme Corp")
    assert 0.5 < confidence < 0.8


def test_document_scoring():
    scorer = ConfidenceScorer()
    fields = {
        "invoice_number": "INV-12345",
        "vendor_name": "Acme Corp",
        "total_amount": "$500.00",
        "issue_date": "2024-01-01",
        "due_date": None,
    }
    scored = scorer.score_document(fields)
    assert len(scored) == 5
    assert scored["invoice_number"]["confidence"] >= 0.9
    assert scored["due_date"]["confidence"] == 0.0
    assert all("confidence" in v for v in scored.values())
