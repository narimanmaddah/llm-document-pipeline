# Enhanced Example Script with Pipeline Trace

**Date:** 2026-04-21  
**Scope:** Add a runnable end-to-end example showing document flow through all pipeline stages with formatted output at each step.

---

## Problem Statement

The current `example.py` demonstrates the API but doesn't show what the pipeline actually *does* at each stage. New users can't visualize:
- What quality gating looks like in practice
- How PII detection finds and redacts sensitive data
- What confidence scores mean in context
- What gets routed to human review and why

This design adds a concrete walkthrough: real invoice → quality check → OCR → PII redaction → LLM extraction → final output.

---

## Solution Overview

Create an enhanced example script that processes a synthetic test invoice end-to-end and prints formatted output at each pipeline stage. Users run `python example.py` once and see the complete trace printed to console.

### Components

**1. Test Fixture: `tests/fixtures/sample_invoice.txt`**
- Realistic invoice content with embedded PII (person names, email addresses, tax IDs, IBANs)
- ~500 words, representative of typical business invoices
- Includes multilingual content or special formatting to showcase pipeline capabilities
- Safe for committed test data (synthetic, no real sensitive info)

**2. Enhanced `example.py` Script**
Refactored to:
- Load or generate the test invoice
- Process through pipeline with error handling
- Print section-by-section output:
  - **Input**: Original invoice text (first 200 chars + "...")
  - **Quality Gate**: Score + pass/fail + routing decision
  - **OCR/Language Detection**: Extracted text + language code
  - **PII Detection**: Count of entities by type (e.g., 2 PERSON, 1 EMAIL, 1 IBAN)
  - **Redaction**: Before/after text showing redaction (side-by-side or sequential)
  - **LLM Extraction**: Structured fields with confidence scores in table format
  - **Validation & Routing**: Review queue decision + reason

**3. Optional: `EXAMPLE_OUTPUT.txt`**
- Baked output from a successful pipeline run
- Can be generated from script output (not manually written)
- Helps users compare their output against expected result

### Data Flow

```
Sample Invoice (synthetic)
        ↓
Quality Gate Check
   Score: 0.87 ✓ Pass
        ↓
OCR Extraction
   Language: en
   Text: [350 chars] ...
        ↓
PII Detection
   Found: 2 PERSON, 1 EMAIL, 1 IBAN
        ↓
PII Redaction
   Before: "John Smith (john@example.com)"
   After:  "[PERSON_1] ([EMAIL_1])"
        ↓
LLM Extraction
   Fields extracted with confidence
        ↓
Validation & Routing
   All fields ≥ 0.80: Auto-approve
```

### Output Format

All sections use:
- **Headers** (`=====`) to clearly separate stages
- **Tables** for field-level data (confidence scores, PII entities)
- **Side-by-side diffs** for before/after redaction
- **Metrics summary** at the end (quality score, confidence stats, review rate)

### Error Handling

If any stage fails (e.g., model weights missing, API timeout):
- Print the stage name and error message
- Continue to next stage where possible
- Note: "Pipeline halted at [stage]"

### Execution

```bash
python example.py
```

Output goes to stdout. Optional: support `--verbose` for intermediate details.

---

## Design Decisions

**Why a script vs. a documentation file?**
- Users see *real* outputs, not hardcoded examples
- Runs on their machine with their config
- Can be updated alongside pipeline changes without manual doc rewrites

**Why synthetic data in fixtures?**
- Safe to commit (no real PII)
- Consistent across runs
- Clearly demonstrates PII detection/redaction

**Why print sections separately?**
- Easier to understand the pipeline's structure
- Users can focus on one stage at a time
- Educational — shows data transformations

---

## Acceptance Criteria

- [ ] Script runs without errors: `python example.py`
- [ ] Output shows all 7 stages in sequence
- [ ] Quality gate score, PII entities, and confidence scores are visible
- [ ] Redaction before/after is clear and unambiguous
- [ ] Output is reproducible (same test invoice → same output)
- [ ] Script handles missing config/model gracefully with helpful error
- [ ] Total runtime < 10 seconds (excluding model loading)
- [ ] README updated with "Run the example" section linking to script

---

## Out of Scope

- Interactive mode / user prompts
- Batch processing multiple documents
- Export to different formats (JSON, CSV)
- Performance benchmarking or timing details
