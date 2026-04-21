# Architecture & Design

## Overview

The pipeline processes documents through six sequential stages, with quality gates and human-in-the-loop routing built in from the start.

```
Input Document
      ↓
   Quality Gate (Image analysis)
      ↓
   OCR + Language Detection
      ↓
   PII Detection & Redaction
      ↓
   LLM-Based Extraction
      ↓
   Confidence Scoring
      ↓
   Validation & Routing (Human review if needed)
      ↓
   Structured JSON Output
```

## Design Principles

### 1. Quality Gates Before LLM

Running low-quality scans through an LLM wastes tokens and produces unreliable results. The quality classifier runs first and routes problematic documents **before** reaching the expensive extraction step.

**Implementation**: `QualityClassifier` analyzes brightness, contrast, sharpness, and skew. Documents scoring below `route_to_review_below` threshold skip LLM entirely.

### 2. Per-Field Confidence Scoring

A document may be 95% extractable with two ambiguous fields. Per-field confidence enables reviewers to focus on exactly what is uncertain, not reprocess the whole document.

**Implementation**: `ConfidenceScorer` uses pattern matching (regex) for high-confidence signals (e.g., invoice numbers match `INV-\d+`). Base score 0.7 for extracted values; 0.95+ for pattern matches.

### 3. PII Never Persists Beyond Redaction

Raw extracted text containing PII is held only **in-memory** during processing. The audit log records *that* PII was present and handled, not what the PII was.

**Implementation**: `PIIRedactor` redacts text before sending to LLM, then discards the original. `PipelineResult.raw_text` is always `None` on return. Audit trail written to JSONL with counts and types, not values.

### 4. Prompt Versioning

LLM outputs are sensitive to prompt changes. Every extraction is tagged with the prompt version that produced it, enabling reproducibility and regression testing.

**Implementation**: `LLMExtractor` stores multiple prompt templates (v1, v2, etc.) keyed by version. Config specifies active version. Future: timestamp prompts and track output drift per version.

## Component Details

### `QualityClassifier`

**Purpose**: Early-stage filtering to prevent wasting LLM tokens on low-quality inputs.

**Algorithm**:
- Brightness score: How close is average pixel intensity to 140 (typical readable text)?
- Contrast score: Variance in pixel values (readable text has high variance)
- Sharpness score: Laplacian variance (crisp edges vs blurry)
- Skew score: Hough line detection to identify rotated documents

**Score**: Weighted average [0-1]

**Config**:
- `min_quality_score`: Accept for processing
- `route_to_review_below`: Route to human, skip LLM

### `OCRExtractor`

**Purpose**: Convert image/PDF to text.

**Implementation**: Tesseract OCR via `pytesseract`. Can accept file paths or raw bytes.

**Limitations**: Quality depends on image quality (hence the quality gate upstream).

### `LanguageDetector`

**Purpose**: Identify document language for potential downstream translation or language-specific validation.

**Implementation**: `langdetect` library (CLD3-based). Returns ISO 639-1 code (e.g., 'en', 'de', 'es').

### `PIIDetector`

**Purpose**: Identify sensitive data so it can be redacted before LLM processing.

**Patterns Supported**:
- EMAIL: Standard email regex
- PHONE: US phone format (555-123-4567, +1 555 123 4567, etc.)
- IBAN: EU/intl bank account format
- TAX_ID: US SSN/EIN format (XX-XXXXXXX)
- PERSON: Names with titles (Mr. Smith, Dr. Johnson)

**Extensible**: Add patterns to `PATTERNS` dict for custom entity types.

### `PIIRedactor`

**Purpose**: Replace PII with `[REDACTED]` marker; audit log (not the values).

**Behavior**:
- Detects PII using `PIIDetector`
- Replaces matches with `[REDACTED]`
- Logs to audit trail: timestamp, entity types found, count (not values)
- Returns redacted text + metadata

**Audit Trail**: JSONL file, each line:
```json
{
  "timestamp": "2024-04-21T...",
  "pii_detected": true,
  "entity_types_found": ["EMAIL", "PHONE"],
  "count": 2
}
```

### `LLMExtractor`

**Purpose**: Structured extraction using LLM prompts.

**Prompt Templates**:
```
v1_invoice: Extract invoice fields (number, vendor, amount, dates)
v2_invoice: (future) variant with different prompt wording
```

**Flow**:
1. Load prompt template for specified version
2. Format with redacted text
3. Call OpenAI API (configurable model)
4. Parse JSON response
5. Return extracted fields dict

**Error Handling**: JSON parse errors return empty dict; caller decides whether to route for review.

### `ConfidenceScorer`

**Purpose**: Score likelihood of correct extraction per field.

**Scoring**:
- Null/empty: 0.0
- Pattern match (e.g., invoice matches `INV-\d+`): 0.95
- Generic value: 0.7

**Patterns**:
- `invoice_number`: `INV-\d+`, `INV\d+`, `#\d{6,}`
- `total_amount`: `$[\d,]+\.\d{2}`, `€[\d,]+\.\d{2}`
- `issue_date`: `YYYY-MM-DD`, `MM/DD/YYYY`

**Extensible**: Add field → patterns mapping to `PATTERNS` dict.

### `SchemaValidator`

**Purpose**: Validate extracted data conforms to schema.

**Schema**: `InvoiceSchema` (Pydantic model) with optional fields.

**Returns**: (is_valid: bool, result: dict) tuple.

### `ReviewRouter`

**Purpose**: Decide whether document needs human review based on quality, confidence, and PII.

**Routes to Review If**:
- Quality score < 0.70
- Any field confidence < `field_review_threshold` (default 0.80)
- PII was detected (human verifies redaction)

**Routes to Auto-Approve If**:
- Quality ≥ 0.85
- All fields ≥ `document_auto_approve` (default 0.90)
- No PII detected

### `DocumentPipeline`

**Purpose**: Orchestrate all stages.

**Flow**:
1. Quality gate → route low-quality to review
2. OCR extract → language detect
3. Redact PII
4. LLM extract (on redacted text)
5. Score confidence
6. Validate schema
7. Route to review if needed
8. Return result

**Batch Mode**: `process_batch()` wraps each document; errors logged, pipeline continues.

## Data Flow & Security

### PII Handling

```
Raw Text (from OCR)
    ↓
[PIIDetector]  ← Detects: PERSON, EMAIL, PHONE, etc.
    ↓
[PIIRedactor]  ← Redacts → [REDACTED]
    ↓
Redacted Text (safe for LLM)
    ↓
[LLMExtractor]
    ↓
Raw Text discarded (never persisted)
Audit log written (no actual PII values)
```

### Result Object

`PipelineResult` contains:
- `extracted_fields`: Dict with confidence scores
- `quality_score`: 0-1 metric
- `language`: ISO 639-1 code
- `requires_review`: Boolean flag
- `pii_detected`: Whether PII was found + redacted
- `confidence_summary`: Min/avg/max confidence
- `raw_text`: Always `None` (security: prevents accidental exposure)

## Extending the Pipeline

### Add a New Document Type

1. **Create Schema** (e.g., `ReceiptSchema` in `validation/schema.py`)
2. **Add Prompt Template** (e.g., `v1_receipt` in `extraction/llm_extractor.py`)
3. **Update Config** (set `prompt_version: v1_receipt`)
4. **Test** (write tests for new fields)

Example:
```python
# In llm_extractor.py
PROMPT_TEMPLATES = {
    "v1_invoice": "...",
    "v1_receipt": """Extract from receipt:
- receipt_id
- merchant_name
- total
- items (list)
- date
Return JSON only."""
}
```

### Add Custom PII Type

```python
# In pii/detector.py
PATTERNS = {
    "EMAIL": r"...",
    "CREDIT_CARD": r"\b(?:\d{4}[-\s]?){3}\d{4}\b"  # Add this
}
```

Then reference in config: `entities_to_detect: [EMAIL, CREDIT_CARD]`

### Improve Quality Classifier

Production deployments train a CNN on domain-specific documents:

```python
# Replace heuristic with model
class QualityClassifier:
    def __init__(self, model_path: str):
        self.model = load_model(model_path)
    
    def score(self, image_path: str) -> float:
        image = preprocess(image_path)
        return self.model.predict(image)[0]
```

## Monitoring & Observability

### Metrics Exported

- `doc_quality_score`: Distribution of quality scores
- `extraction_confidence_p50/p95`: Field confidence percentiles
- `human_review_rate`: % routed to review
- `pii_detection_rate`: % with PII
- `prompt_version_distribution`: Extractions per prompt version

### Logs

- **Audit log** (`logs/pii_audit.jsonl`): PII detection events (no values)
- **Application logs**: Errors, pipeline progress (future: integrate structured logging)

### Future: Drift Detection

Compare field distributions across time:
- Did model outputs shift?
- Are confidence scores trending down?
- Is PII detection pattern changing?

```python
# Sketch for future implementation
drift_detector = DriftDetector(window_days=7)
drift_report = drift_detector.analyze(recent_extractions)
if drift_report.detected:
    alert("Extraction drift detected: %s" % drift_report.reason)
```

## Performance Considerations

- **Quality Classification**: ~100ms per image (lightweight heuristics)
- **OCR**: 500ms–2s per page (Tesseract)
- **PII Detection**: ~50ms per 1000 characters (regex)
- **LLM Extraction**: 1–5s per document (API latency + inference)
- **Total**: ~2–8s per document depending on image quality and LLM model

### Bottleneck: LLM

Batch inference or async processing recommended for high volume:
```python
# Future: async LLM calls
results = await pipeline.process_async_batch(documents)
```

## Testing Strategy

- **Unit Tests**: PII detection, confidence scoring, routing logic
- **Integration Tests**: Full pipeline on synthetic documents
- **Regression Tests**: Verify prompt versions produce consistent outputs
- **No Real PII**: Test suite uses synthetic data only

Run tests:
```bash
pytest tests/ -v
```
