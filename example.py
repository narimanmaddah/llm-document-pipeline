#!/usr/bin/env python3
"""End-to-end pipeline example with stage-by-stage output formatting."""

import os
from pathlib import Path
from pipeline import DocumentPipeline, PipelineConfig
from pipeline.pii.redactor import PIIRedactor

# ============================================================================
# Output Formatting Utilities
# ============================================================================

def print_section(title: str, level: int = 1):
    """Print a section header."""
    if level == 1:
        print(f"\n{'=' * 80}")
        print(f"{title.upper()}")
        print(f"{'=' * 80}")
    elif level == 2:
        print(f"\n{title}")
        print(f"{'-' * len(title)}")


def print_key_value_pairs(data: dict, indent: int = 0):
    """Print dictionary as key-value pairs."""
    prefix = " " * indent
    for key, value in data.items():
        # Format value for readability
        if isinstance(value, float):
            formatted_value = f"{value:.4f}"
        elif isinstance(value, bool):
            formatted_value = "✓ Yes" if value else "✗ No"
        elif isinstance(value, list):
            formatted_value = ", ".join(str(v) for v in value)
        else:
            formatted_value = str(value)

        print(f"{prefix}{key:.<30} {formatted_value}")


def print_table(headers: list, rows: list, col_widths: list = None):
    """Print a formatted table."""
    if not rows:
        print("  (No data)")
        return

    # Calculate column widths if not provided
    if col_widths is None:
        col_widths = []
        for i, header in enumerate(headers):
            max_width = len(header)
            for row in rows:
                if i < len(row):
                    max_width = max(max_width, len(str(row[i])))
            col_widths.append(max_width + 2)

    # Print header
    header_row = " | ".join(h.ljust(w) for h, w in zip(headers, col_widths))
    print(f"  {header_row}")
    print(f"  {'-' * len(header_row)}")

    # Print rows
    for row in rows:
        row_str = " | ".join(str(v).ljust(w) for v, w in zip(row, col_widths))
        print(f"  {row_str}")


def truncate_text(text: str, max_chars: int = 150) -> str:
    """Truncate text for display."""
    if len(text) > max_chars:
        return text[:max_chars] + "..."
    return text


def count_pii_entities(pii_metadata: dict) -> dict:
    """Count PII entities by type."""
    counts = {}
    if "pii_types" in pii_metadata:
        for entity_type in pii_metadata["pii_types"]:
            counts[entity_type] = counts.get(entity_type, 0) + 1
    return counts


# ============================================================================
# Main Example Pipeline Run
# ============================================================================

def main():
    """Process a sample invoice through the pipeline with detailed output."""

    print_section("LLM Document Pipeline - End-to-End Example", level=1)

    # Load configuration
    print("\nLoading configuration...")
    try:
        config = PipelineConfig.from_yaml("config/pipeline_config.yaml")
        print("✓ Configuration loaded successfully")
    except Exception as e:
        print(f"✗ Error loading config: {e}")
        print("  Using default paths. Ensure config/pipeline_config.yaml exists.")
        return

    # Load sample invoice
    fixture_path = Path("tests/fixtures/sample_invoice.txt")
    if not fixture_path.exists():
        print(f"✗ Sample invoice fixture not found: {fixture_path}")
        return

    with open(fixture_path, "r") as f:
        invoice_text = f.read()

    print(f"✓ Loaded sample invoice ({len(invoice_text)} chars)")

    # ========================================================================
    # STAGE 1: INPUT
    # ========================================================================
    print_section("Stage 1: Document Input", level=2)
    print(f"Document path: {fixture_path.absolute()}")
    print(f"Document size: {len(invoice_text)} characters")
    print(f"\nFirst 200 characters of invoice:")
    print(f"  {truncate_text(invoice_text, 200)}")

    # ========================================================================
    # STAGE 2: QUALITY GATE
    # ========================================================================
    print_section("Stage 2: Quality Gate", level=2)
    quality_score = 0.85  # Default pass score for demo
    try:
        pipeline = DocumentPipeline(config)
        # Check if file is a real image (not a text fixture)
        if fixture_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif']:
            quality_score = pipeline.quality_classifier.score(str(fixture_path))
            print_key_value_pairs({
                "Quality Score": quality_score,
                "Min Threshold": config.quality_gate.min_quality_score,
                "Review Below": config.quality_gate.route_to_review_below,
                "Status": "✓ PASS" if quality_score >= config.quality_gate.min_quality_score else "✗ FAIL",
            })

            if quality_score < config.quality_gate.route_to_review_below:
                print_section("Pipeline Halted: Document quality too low for processing", level=2)
                return
        else:
            print_key_value_pairs({
                "Quality Check": "SKIPPED (text fixture)",
                "Assumed Quality": quality_score,
                "Note": "Text files bypass image-based quality scoring",
            })

    except Exception as e:
        print(f"⚠ Warning: Could not run quality classifier: {e}")
        print("  Proceeding with pipeline (quality gate skipped)")
        quality_score = 0.85  # Assume pass for demo

    # ========================================================================
    # STAGE 3: OCR & LANGUAGE DETECTION
    # ========================================================================
    print_section("Stage 3: OCR & Language Detection", level=2)
    raw_text = invoice_text  # Use invoice text as fallback
    language = "en"  # Default language

    # Try OCR if file is an image
    if fixture_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif']:
        try:
            raw_text = pipeline.ocr_extractor.extract_text(str(fixture_path))
        except Exception as e:
            print(f"⚠ Warning: OCR extraction failed: {e}")
    else:
        print_key_value_pairs({
            "Source": "Text fixture (OCR skipped)",
            "Extraction Method": "Direct text reading",
        })

    # Always detect language
    try:
        language = pipeline.language_detector.detect_language(raw_text)
        print_key_value_pairs({
            "Detected Language": language.upper() if language else "UNKNOWN",
            "Extracted Text Length": len(raw_text),
        })
        print(f"\nExtracted text (first 300 chars):")
        print(f"  {truncate_text(raw_text, 300)}")
    except Exception as e:
        print(f"⚠ Warning: Language detection failed: {e}")
        language = "en"

    # ========================================================================
    # STAGE 4: PII DETECTION & REDACTION
    # ========================================================================
    print_section("Stage 4: PII Detection & Redaction", level=2)
    try:
        redactor = PIIRedactor(audit_log_path="logs/pii_audit.jsonl")
        redacted_text, pii_metadata = redactor.redact(raw_text, config.pii.entities_to_detect)

        pii_counts = count_pii_entities(pii_metadata)

        print_key_value_pairs({
            "PII Detected": pii_metadata.get("pii_detected", False),
            "Entity Types Found": ", ".join(pii_metadata.get("pii_types", [])),
            "Total Redactions": pii_metadata.get("redaction_count", 0),
            "Redaction Mode": pii_metadata.get("redaction_mode", "replace"),
        })

        if pii_counts:
            print("\nEntities by Type:")
            rows = [[entity_type, count] for entity_type, count in sorted(pii_counts.items())]
            print_table(["Entity Type", "Count"], rows, col_widths=[20, 10])

        # Show before/after sample
        print("\nBefore/After Redaction Sample:")
        print(f"  BEFORE: {truncate_text(raw_text, 150)}")
        print(f"  AFTER:  {truncate_text(redacted_text, 150)}")

    except Exception as e:
        print(f"⚠ Warning: PII redaction failed: {e}")
        redacted_text = raw_text
        pii_metadata = {"pii_detected": False, "pii_types": [], "redaction_count": 0}

    # ========================================================================
    # STAGE 5: LLM EXTRACTION
    # ========================================================================
    print_section("Stage 5: LLM Extraction", level=2)
    try:
        extracted_fields = pipeline.llm_extractor.extract(redacted_text, config.llm.prompt_version)

        print_key_value_pairs({
            "LLM Model": config.llm.model,
            "Prompt Version": config.llm.prompt_version,
            "Fields Extracted": len(extracted_fields),
        })

        print("\nRaw Extracted Fields:")
        for field_name, field_value in extracted_fields.items():
            field_type = type(field_value).__name__
            field_display = truncate_text(str(field_value), 100)
            print(f"  • {field_name:.<30} {field_display} ({field_type})")

    except Exception as e:
        print(f"⚠ Warning: LLM extraction failed: {e}")
        extracted_fields = {}
        print(f"  Proceeding with empty extraction (LLM extraction skipped)")

    # ========================================================================
    # STAGE 6: CONFIDENCE SCORING
    # ========================================================================
    print_section("Stage 6: Confidence Scoring & Validation", level=2)
    try:
        scored_fields = pipeline.confidence_scorer.score_document(extracted_fields)
        confidence_summary = pipeline.review_router.get_confidence_summary(scored_fields)

        print_key_value_pairs({
            "Field Review Threshold": config.confidence.field_review_threshold,
            "Auto-Approve Threshold": config.confidence.document_auto_approve,
        })

        if confidence_summary:
            print("\nConfidence Summary:")
            print_key_value_pairs(confidence_summary, indent=2)

        # Show confidence per field
        if scored_fields:
            print("\nExtracted Fields with Confidence:")
            rows = []
            for field_name, field_data in scored_fields.items():
                if isinstance(field_data, dict) and "confidence" in field_data:
                    value = field_data.get("value", "N/A")
                    confidence = field_data.get("confidence", 0.0)
                    rows.append([field_name, f"{confidence:.4f}", truncate_text(str(value), 50)])
                else:
                    rows.append([field_name, "N/A", truncate_text(str(field_data), 50)])

            if rows:
                print_table(["Field Name", "Confidence", "Value"], rows, col_widths=[25, 15, 50])

    except Exception as e:
        print(f"⚠ Warning: Confidence scoring failed: {e}")
        scored_fields = extracted_fields
        confidence_summary = {}

    # ========================================================================
    # STAGE 7: VALIDATION & HUMAN-IN-THE-LOOP ROUTING
    # ========================================================================
    print_section("Stage 7: Validation & Routing", level=2)
    try:
        is_valid, validated = pipeline.schema_validator.validate(scored_fields)
        requires_review = pipeline.review_router.should_route_for_review(
            scored_fields, quality_score, pii_metadata.get("pii_detected", False)
        )

        print_key_value_pairs({
            "Schema Valid": is_valid,
            "Requires Human Review": requires_review,
            "Reason for Review": (
                "Low confidence fields detected" if requires_review and scored_fields else
                "PII detected" if requires_review and pii_metadata.get("pii_detected") else
                "None — auto-approved"
            ),
        })

    except Exception as e:
        print(f"⚠ Warning: Validation failed: {e}")
        is_valid = False
        requires_review = True

    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    print_section("Pipeline Execution Summary", level=2)
    print_key_value_pairs({
        "Quality Score": quality_score,
        "Language": language.upper() if language else "UNKNOWN",
        "PII Detected": pii_metadata.get("pii_detected", False),
        "Fields Extracted": len(scored_fields),
        "Schema Valid": is_valid,
        "Requires Review": requires_review,
    })

    print("\n✓ Pipeline execution completed successfully\n")


if __name__ == "__main__":
    main()
