# llm-document-pipeline

A production-grade multilingual document intelligence pipeline combining OCR, image classification, and LLM-based extraction — with quality gating, PII controls, and confidence scoring built in from the start.

---

## The Problem

Most document processing demos show the happy path: a clean PDF goes in, structured JSON comes out. Production is different.

Documents arrive as scanned PDFs, phone photos, faxes, and email screenshots. Quality varies enormously. Content is multilingual. PII must never leave the system uncontrolled. And when the model is uncertain, a human needs to know — not find out later when the data is already in a database.

This pipeline is designed for that reality.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DOCUMENT INTAKE                          │
│          PDF / image / scanned input accepted               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 QUALITY GATE (Stage 1)                      │
│   CNN image classifier: legibility, orientation, scan       │
│   quality score. Low-quality docs routed to human review.   │
└────────────────────┬────────────────────────────────────────┘
                     │ Quality score ≥ threshold
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  OCR + PRE-PROCESSING                       │
│   Text extraction · Language detection · Normalisation      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│               PII DETECTION & REDACTION                     │
│   Entity recognition · PII tagging · Audit log entry        │
│   Raw text never persisted beyond this stage                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              LLM EXTRACTION (Stage 2)                       │
│   Structured field extraction · Translation if required     │
│   Confidence scoring per field · Prompt versioning          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│            VALIDATION & HUMAN-IN-THE-LOOP ROUTING           │
│   Schema validation · Low-confidence fields flagged         │
│   Selective human review queue for uncertain outputs        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  STRUCTURED OUTPUT                          │
│         JSON / database · Audit trail · Metrics             │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

**Quality gates before the LLM, not after.** Running a low-quality scan through an LLM wastes tokens and produces unreliable output. A lightweight CNN quality classifier runs first and routes problematic documents before they reach the expensive extraction step.

**Confidence scoring per field, not per document.** A document can be 95% extractable with two ambiguous fields. Flagging the whole document for review wastes human time. Per-field confidence scores let reviewers focus on exactly what is uncertain.

**PII is never persisted beyond the redaction stage.** Raw extracted text containing PII is held only in memory during processing. The audit log records that PII was present and handled, not what the PII was.

**Prompt versioning is not optional.** LLM outputs are sensitive to prompt changes. Every prompt has a version identifier. Extraction results are tagged with the prompt version that produced them, enabling reproducibility and regression testing.

---

## Project Structure

```
llm-document-pipeline/
├── pipeline/
│   ├── quality_gate/
│   │   ├── classifier.py          # CNN quality scorer
│   │   ├── thresholds.py          # Configurable quality thresholds
│   │   └── models/                # Pretrained quality model weights
│   ├── ocr/
│   │   ├── extractor.py           # OCR engine wrapper
│   │   └── language_detection.py  # Language identification
│   ├── pii/
│   │   ├── detector.py            # PII entity recognition
│   │   ├── redactor.py            # Redaction with audit logging
│   │   └── audit.py               # Immutable audit trail
│   ├── extraction/
│   │   ├── llm_extractor.py       # LLM extraction with retry logic
│   │   ├── prompts/               # Versioned prompt templates
│   │   │   ├── v1_invoice.yaml
│   │   │   └── v2_invoice.yaml
│   │   └── confidence.py          # Per-field confidence scoring
│   ├── validation/
│   │   ├── schema.py              # Output schema validation
│   │   └── routing.py             # Human review queue router
│   └── pipeline.py                # Orchestration entrypoint
├── monitoring/
│   ├── metrics.py                 # Extraction rate, confidence dist.
│   └── drift.py                   # Prompt output drift detection
├── tests/
│   ├── test_quality_gate.py
│   ├── test_extraction.py
│   ├── test_pii_redaction.py
│   └── fixtures/                  # Synthetic test documents
├── notebooks/
│   └── pipeline_walkthrough.ipynb # End-to-end example
├── config/
│   └── pipeline_config.yaml
├── requirements.txt
└── README.md
```

---

## Quickstart

```bash
git clone https://github.com/narimanmaddah/llm-document-pipeline
cd llm-document-pipeline
pip install -r requirements.txt
```

```python
from pipeline import DocumentPipeline
from pipeline.config import PipelineConfig

config = PipelineConfig.from_yaml("config/pipeline_config.yaml")
pipeline = DocumentPipeline(config)

result = pipeline.process("path/to/document.pdf")

print(result.extracted_fields)
# {'invoice_number': {'value': 'INV-2024-0042', 'confidence': 0.97},
#  'total_amount':   {'value': '1,842.50', 'confidence': 0.94},
#  'vendor_name':    {'value': 'Acme GmbH', 'confidence': 0.89},
#  'issue_date':     {'value': '2024-03-15', 'confidence': 0.99}}

print(result.quality_score)        # 0.91
print(result.requires_review)      # False
print(result.pii_detected)         # True (handled; not logged)
```

---

## Configuration

```yaml
# config/pipeline_config.yaml

quality_gate:
  min_quality_score: 0.75
  route_to_review_below: 0.60

llm:
  provider: openai
  model: gpt-4o
  prompt_version: v2_invoice
  max_retries: 3

confidence:
  field_review_threshold: 0.80   # Fields below this go to review queue
  document_auto_approve: 0.90    # All fields above this: auto-approved

pii:
  entities_to_detect: [PERSON, EMAIL, PHONE, IBAN, TAX_ID]
  redaction_mode: replace         # replace | mask | hash
  audit_log_path: logs/pii_audit.jsonl

monitoring:
  metrics_export: prometheus
  drift_window_days: 7
```

---

## Monitoring

The pipeline exposes extraction metrics for observability:

| Metric | Description |
|--------|-------------|
| `doc_quality_score` | Distribution of quality gate scores |
| `extraction_confidence_p50/p95` | Field confidence percentiles |
| `human_review_rate` | Fraction of documents routed to review |
| `pii_detection_rate` | Rate of PII-containing documents |
| `prompt_version_distribution` | Extraction volume by prompt version |

---

## Testing

```bash
pytest tests/ -v
```

Tests use synthetic documents only — no real PII or proprietary content in the test suite.

---

## What This Is Not

This repository demonstrates pipeline architecture, design patterns, and production thinking. The LLM calls use the OpenAI API; swap in any compatible provider. The quality classifier weights included are trained on synthetic data — you would retrain on your own document distribution in production.

---

## Background

This pipeline reflects patterns developed while building a production invoice-processing system processing 10,000+ documents annually across multiple languages, with zero data privacy incidents across all deployments.

---

## Licence

MIT
