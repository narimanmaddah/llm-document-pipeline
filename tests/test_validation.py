import pytest
from pipeline.validation.schema import SchemaValidator, InvoiceSchema
from pipeline.validation.routing import ReviewRouter


def test_invoice_schema_valid():
    validator = SchemaValidator()
    data = {
        "invoice_number": "INV-123",
        "vendor_name": "Acme",
        "total_amount": "$500",
        "issue_date": "2024-01-01",
        "due_date": None,
    }
    is_valid, result = validator.validate(data)
    assert is_valid is True


def test_review_router_low_quality():
    router = ReviewRouter()
    scored_fields = {
        "invoice_number": {"value": "INV-123", "confidence": 0.9},
    }
    assert router.should_route_for_review(scored_fields, quality_score=0.5, pii_detected=False) is True


def test_review_router_low_confidence():
    router = ReviewRouter()
    scored_fields = {
        "invoice_number": {"value": "INV-123", "confidence": 0.6},
    }
    assert router.should_route_for_review(scored_fields, quality_score=0.9, pii_detected=False) is True


def test_review_router_pii_detected():
    router = ReviewRouter()
    scored_fields = {
        "invoice_number": {"value": "INV-123", "confidence": 0.95},
    }
    assert router.should_route_for_review(scored_fields, quality_score=0.9, pii_detected=True) is True


def test_review_router_auto_approve():
    router = ReviewRouter()
    scored_fields = {
        "invoice_number": {"value": "INV-123", "confidence": 0.95},
        "vendor_name": {"value": "Acme", "confidence": 0.92},
    }
    assert router.should_route_for_review(scored_fields, quality_score=0.85, pii_detected=False) is False


def test_confidence_summary():
    router = ReviewRouter()
    scored_fields = {
        "invoice_number": {"value": "INV-123", "confidence": 0.9},
        "vendor_name": {"value": "Acme", "confidence": 0.8},
        "total_amount": {"value": "$500", "confidence": 0.85},
    }
    summary = router.get_confidence_summary(scored_fields)
    assert summary["min"] == 0.8
    assert summary["max"] == 0.9
    assert 0.8 <= summary["avg"] <= 0.9
