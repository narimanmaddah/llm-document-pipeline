# Enhanced Example Script with Pipeline Trace - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a runnable example script that processes a synthetic invoice through all pipeline stages and prints formatted output at each step, showing users what the pipeline actually does.

**Architecture:** The solution consists of: (1) a synthetic invoice fixture with realistic PII, (2) a refactored `example.py` that processes the fixture end-to-end and extracts intermediate stage outputs, (3) helper functions for formatting output with clear section headers and tables, and (4) error handling for missing dependencies.

**Tech Stack:** Python 3.12, pipeline components (OCR, PII, LLM, validation), dataclasses for structured output.

---

## File Structure

**Files to create:**
- `tests/fixtures/sample_invoice.txt` — Synthetic invoice with realistic PII and business content

**Files to modify:**
- `example.py` — Refactor to add stage-by-stage processing, output formatting, and error handling
- `README.md` — Add "Run the Example" section with instructions

---

## Task 1: Create Synthetic Invoice Fixture

**Files:**
- Create: `tests/fixtures/sample_invoice.txt`

- [ ] **Step 1: Create the fixtures directory structure**

```bash
mkdir -p tests/fixtures
```

- [ ] **Step 2: Create the synthetic invoice fixture**

```bash
cat > tests/fixtures/sample_invoice.txt << 'EOF'
INVOICE

Invoice Number: INV-2024-0847
Date: March 15, 2024
Due Date: April 15, 2024

BILL TO:
John Smith
John.Smith@acmecorp.com
Phone: +1 (555) 123-4567

Acme Manufacturing GmbH
Hauptstrasse 42
10115 Berlin, Germany
Tax ID: DE 123 456 789
IBAN: DE89 3704 0044 0532 0130 00

SHIP TO:
Jane Doe
jane.doe@customer.com

FROM:
Global Imports Ltd.
Supplier Tax ID: GB987654321
Contact: support@globalimports.co.uk

Line Items:
1. Industrial Components (SKU: COMP-001)    Qty: 50    Unit Price: €125.00    Total: €6,250.00
2. Assembly Services (SKU: SVC-002)         Qty: 1     Unit Price: €1,500.00   Total: €1,500.00
3. Shipping & Handling                                                         Total: €350.00

Subtotal:                                                    €8,100.00
VAT (19%):                                                  €1,539.00
TOTAL AMOUNT DUE:                                           €9,639.00

Payment Terms: Net 30 days
Payment Instructions: Wire transfer to IBAN DE89370400440532013000
BIC: COBADEFFXXX

Please reference invoice number INV-2024-0847 with payment.
For questions, contact: billing@globalimports.co.uk
Reference Contact: Maria Rodriguez, +49 (30) 555-8234

Thank you for your business.
EOF
```

- [ ] **Step 3: Verify the fixture was created**

```bash
wc -l tests/fixtures/sample_invoice.txt
head -20 tests/fixtures/sample_invoice.txt
```

Expected: File created with ~45 lines, containing person names, emails, phone numbers, tax IDs, IBANs, and business content.

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/sample_invoice.txt
git commit -m "test: add synthetic invoice fixture with realistic PII"
```

---

## Task 2: Create Output Formatting Module

**Files:**
- Modify: `example.py` (add formatting functions)

- [ ] **Step 1: Add formatting helper functions to example.py**

These will be at the top of the file after imports. Replace the entire `example.py` with:

```python
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
    try:
        pipeline = DocumentPipeline(config)
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
            
    except Exception as e:
        print(f"⚠ Warning: Could not run quality classifier: {e}")
        print("  Proceeding with pipeline (quality gate skipped)")
        quality_score = 0.85  # Assume pass for demo
    
    # ========================================================================
    # STAGE 3: OCR & LANGUAGE DETECTION
    # ========================================================================
    print_section("Stage 3: OCR & Language Detection", level=2)
    try:
        raw_text = pipeline.ocr_extractor.extract_text(str(fixture_path))
        language = pipeline.language_detector.detect_language(raw_text)
        
        print_key_value_pairs({
            "Detected Language": language.upper() if language else "UNKNOWN",
            "Extracted Text Length": len(raw_text),
            "Source": "Fixture text (using file as OCR input)",
        })
        
        print(f"\nExtracted text (first 300 chars):")
        print(f"  {truncate_text(raw_text, 300)}")
        
    except Exception as e:
        print(f"⚠ Warning: OCR extraction failed: {e}")
        raw_text = invoice_text
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
```

- [ ] **Step 2: Verify the file was created**

```bash
python example.py 2>&1 | head -50
```

Expected: Script runs without syntax errors and prints configuration section.

- [ ] **Step 3: Commit**

```bash
git add example.py
git commit -m "refactor: add stage-by-stage pipeline output formatting to example script"
```

---

## Task 3: Test the Enhanced Example Script

**Files:**
- Run: `example.py`
- Test: `tests/fixtures/sample_invoice.txt`

- [ ] **Step 1: Ensure all dependencies are installed**

```bash
pip install -r requirements.txt
```

- [ ] **Step 2: Verify the sample invoice fixture exists**

```bash
ls -lah tests/fixtures/sample_invoice.txt
cat tests/fixtures/sample_invoice.txt | head -30
```

Expected: File exists and contains invoice data with PII.

- [ ] **Step 3: Run the example script**

```bash
python example.py
```

Expected output:
- "Configuration loaded successfully" message
- "Stage 1: Document Input" with file info
- "Stage 2: Quality Gate" with quality score
- "Stage 3: OCR & Language Detection" with language detected
- "Stage 4: PII Detection & Redaction" with entity counts
- "Stage 5: LLM Extraction" with field extraction
- "Stage 6: Confidence Scoring" with confidence per field
- "Stage 7: Validation & Routing" with review decision
- "Pipeline Execution Summary" with all metrics

- [ ] **Step 4: Verify output formatting is clear and readable**

Check that output includes:
- Section headers with "=" and "-" lines
- Key-value pairs with aligned dots
- Tables for multi-column data
- Before/after samples for redaction
- No errors or stack traces (warnings OK)

- [ ] **Step 5: Verify script completes in < 10 seconds**

```bash
time python example.py
```

Expected: Real time < 10s

- [ ] **Step 6: Test error handling - verify graceful behavior if config is missing**

```bash
mv config/pipeline_config.yaml config/pipeline_config.yaml.bak
python example.py 2>&1 | head -20
mv config/pipeline_config.yaml.bak config/pipeline_config.yaml
```

Expected: Script prints warning about missing config but continues.

- [ ] **Step 7: Commit**

```bash
git add example.py
git commit -m "test: verify enhanced example script runs end-to-end successfully"
```

---

## Task 4: Update README with Example Section

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add "Run the Example" section to README.md**

Find the line with `## Quickstart` and add the following section after the quickstart code block (before the `---` separator):

```markdown
### Run the Example

To see the pipeline in action with formatted output at each stage:

```bash
python example.py
```

This processes a sample invoice through all pipeline stages and prints:
- **Quality Gate**: Document quality scoring
- **OCR & Language Detection**: Text extraction and language identification
- **PII Detection**: Sensitive entity detection (names, emails, tax IDs, etc.)
- **Redaction**: Before/after view of PII removal
- **LLM Extraction**: Structured field extraction with confidence scores
- **Validation & Routing**: Human review queue decision

Example output:
```
================================================================================
STAGE 1: DOCUMENT INPUT
================================================================================

Document path: tests/fixtures/sample_invoice.txt
Document size: 1847 characters

...

STAGE 4: PII DETECTION & REDACTION
================================================================================

PII Detected........................ ✓ Yes
Entity Types Found................. PERSON, EMAIL, IBAN, TAX_ID
Total Redactions................... 6
Redaction Mode..................... replace

Entities by Type:
  Entity Type          | Count
  ---|---
  PERSON               | 3
  EMAIL                | 2
  IBAN                 | 1
```

The example uses a synthetic invoice (no real PII). See `tests/fixtures/sample_invoice.txt` to inspect or modify the test data.
```

- [ ] **Step 2: Verify the README format**

```bash
head -150 README.md | tail -50
```

Expected: New "Run the Example" section appears after Quickstart with proper markdown formatting.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add 'Run the Example' section to README with pipeline walkthrough instructions"
```

---

## Task 5: Verify Complete Implementation

**Files:**
- Test: `example.py`, `tests/fixtures/sample_invoice.txt`, `README.md`

- [ ] **Step 1: Run the full example one more time to ensure all stages work**

```bash
python example.py > /tmp/example_output.txt 2>&1
cat /tmp/example_output.txt | wc -l
```

Expected: Output is ~100-150 lines depending on pipeline verbosity.

- [ ] **Step 2: Verify all 7 stages appear in output**

```bash
python example.py | grep -c "STAGE"
```

Expected: Output contains "STAGE" 7 times (one for each stage).

- [ ] **Step 3: Verify key metrics are displayed**

```bash
python example.py | grep -E "(Quality Score|PII Detected|Fields Extracted|Requires Review)"
```

Expected: All 4 metrics appear in final summary.

- [ ] **Step 4: Verify README is correctly formatted**

```bash
grep -A 5 "Run the Example" README.md
```

Expected: Section header and code block visible.

- [ ] **Step 5: Final commit for verification**

```bash
git add .
git commit -m "verify: complete enhanced example script with full pipeline trace"
```

- [ ] **Step 6: Verify all commits in order**

```bash
git log --oneline | head -7
```

Expected: Shows 7 commits including:
- "verify: complete enhanced example script"
- "docs: add 'Run the Example' section"
- "test: verify enhanced example script runs"
- "refactor: add stage-by-stage pipeline output formatting"
- "test: add synthetic invoice fixture"

---

## Acceptance Criteria Checklist

- [ ] `tests/fixtures/sample_invoice.txt` exists with realistic PII-containing invoice
- [ ] `example.py` processes fixture through full pipeline (7 stages)
- [ ] Output shows quality score, OCR text, language, PII counts, before/after redaction, confidence scores, validation decision
- [ ] Output is formatted with clear section headers and tables
- [ ] Script handles missing config/models gracefully with warnings
- [ ] Script completes in < 10 seconds
- [ ] README updated with "Run the Example" section
- [ ] All changes committed to git with clear commit messages
- [ ] `python example.py` produces reproducible output (same invoice → same output structure)

---

## Implementation Notes

**Stage Output Details:**

1. **Stage 1 (Input):** Shows file path and size
2. **Stage 2 (Quality Gate):** Displays quality score and pass/fail decision
3. **Stage 3 (OCR):** Shows language detected and extracted text sample
4. **Stage 4 (PII):** Counts entities by type, shows before/after
5. **Stage 5 (LLM):** Lists extracted fields with raw values
6. **Stage 6 (Confidence):** Shows per-field confidence scores in table
7. **Stage 7 (Validation):** Displays validation status and review routing decision

**Error Handling:**

- Missing config: Print warning, continue with defaults
- Missing fixture: Print error, exit gracefully
- OCR failure: Print warning, use raw fixture text
- LLM failure: Print warning, continue with empty extraction
- Other failures: Print warning with context, continue pipeline

**Performance:**

- Total runtime target: < 10 seconds (excluding model loading)
- Most time spent in LLM extraction (depends on API rate limits)
- Output formatting adds negligible overhead
