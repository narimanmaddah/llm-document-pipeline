# Quick Start Guide

## Installation

```bash
# Clone and install
git clone https://github.com/narimanmaddah/llm-document-pipeline
cd llm-document-pipeline
pip install -r requirements.txt
```

Note: `pytesseract` requires Tesseract OCR to be installed on your system:
- **macOS**: `brew install tesseract`
- **Ubuntu/Debian**: `apt-get install tesseract-ocr`
- **Windows**: Download from [GitHub Tesseract releases](https://github.com/UB-Mannheim/tesseract/wiki)

## Set Up OpenAI API Key

```bash
export OPENAI_API_KEY="sk-..."
```

## Run Tests

```bash
pytest tests/ -v
```

Expected output: ~20 tests covering PII detection, confidence scoring, validation, and routing.

## Basic Usage

```python
from pipeline import DocumentPipeline, PipelineConfig

# Load configuration
config = PipelineConfig.from_yaml("config/pipeline_config.yaml")

# Create pipeline
pipeline = DocumentPipeline(config)

# Process a document
result = pipeline.process("path/to/invoice.pdf")

# Access results
print(result.extracted_fields)
# {
#   'invoice_number': {'value': 'INV-123', 'confidence': 0.97},
#   'vendor_name': {'value': 'Acme Corp', 'confidence': 0.91},
#   'total_amount': {'value': '$500.00', 'confidence': 0.98},
#   'issue_date': {'value': '2024-01-15', 'confidence': 0.99}
# }

print(result.quality_score)          # 0.85
print(result.language)               # 'en'
print(result.pii_detected)           # True (handled; not exposed)
print(result.requires_review)        # False
print(result.confidence_summary)     # {'min': 0.91, 'avg': 0.96, 'max': 0.99}
```

## Pipeline Stages

### 1. **Quality Gate**
- Analyzes image brightness, contrast, and sharpness
- Routes low-quality documents to human review
- Configurable threshold (default: 0.75 for processing, 0.60 for review)

### 2. **OCR + Language Detection**
- Extracts text from images/PDFs
- Auto-detects document language
- Handles multilingual content

### 3. **PII Detection & Redaction**
- Identifies emails, phone numbers, IBANs, tax IDs, names
- Redacts PII before sending to LLM
- Logs PII presence to audit trail (not the actual values)
- Raw text never written to disk

### 4. **LLM Extraction**
- Uses OpenAI API (configurable model)
- Extracts structured fields: invoice_number, vendor_name, total_amount, issue_date, due_date
- Per-field confidence scores based on regex pattern matching
- Integrates prompt versioning for reproducibility

### 5. **Validation & Routing**
- Validates extracted fields against schema
- Routes documents to human review if:
  - Any field confidence < threshold (default: 0.80)
  - Quality score too low
  - PII was detected
- Returns confidence statistics for prioritization

## Configuration

Edit `config/pipeline_config.yaml` to customize:

```yaml
quality_gate:
  min_quality_score: 0.75          # Minimum to attempt extraction
  route_to_review_below: 0.60      # Below this, skip LLM

llm:
  model: gpt-4o-mini               # or gpt-4, gpt-3.5-turbo, etc.
  prompt_version: v1_invoice       # Custom prompt templates in pipeline/extraction/prompts/
  temperature: 0.1                 # Lower = more deterministic

confidence:
  field_review_threshold: 0.80     # Route if any field below this
  document_auto_approve: 0.90      # Auto-approve if all fields above this

pii:
  entities_to_detect:
    - PERSON
    - EMAIL
    - PHONE
    - IBAN
    - TAX_ID
  redaction_mode: replace          # or mask, hash
  audit_log_path: logs/pii_audit.jsonl
```

## Batch Processing

```python
documents = ["invoice1.pdf", "invoice2.pdf", "invoice3.pdf"]
results = pipeline.process_batch(documents)

for doc, result in zip(documents, results):
    if result.requires_review:
        print(f"{doc}: flagged for review")
    else:
        print(f"{doc}: auto-approved, confidence avg={result.confidence_summary['avg']}")
```

## PII Example

```python
from pipeline.pii.redactor import PIIRedactor

redactor = PIIRedactor()
text = "Invoice from John Smith (john@example.com), Tax ID: 12-3456789"

redacted, metadata = redactor.redact(
    text, 
    entities_to_detect=["PERSON", "EMAIL", "TAX_ID"]
)

print(redacted)
# "Invoice from [REDACTED] ([REDACTED]), Tax ID: [REDACTED]"

print(metadata)
# {
#   'pii_detected': True,
#   'pii_types': ['PERSON', 'EMAIL', 'TAX_ID'],
#   'redaction_count': 3,
#   'timestamp': '2024-04-21T...'
# }
```

## Example Script

Run the interactive example:

```bash
python3 example.py
```

This demonstrates PII detection and the overall pipeline configuration.

## What's Implemented

✅ Quality gate with heuristic-based image scoring  
✅ OCR extraction and language detection  
✅ Regex-based PII detection and redaction  
✅ LLM extraction with OpenAI API  
✅ Per-field confidence scoring  
✅ Schema validation  
✅ Human-in-the-loop routing  
✅ Audit logging for PII handling  
✅ Batch processing  
✅ Comprehensive test suite  

## Limitations & Future Work

- Quality classifier uses heuristics; production deployments train a CNN on domain-specific data
- LLM extraction currently supports invoice schema only (easily extensible)
- No database persistence layer (add as needed)
- No distributed job queue (add Celery/RQ for scale)
- Monitoring exports to stdout; integrate Prometheus/Grafana for production

## Extending

To add support for a new document type (e.g., receipts):

1. Add new prompt template in `pipeline/extraction/llm_extractor.py`
2. Extend schema in `pipeline/validation/schema.py`
3. Update config with new prompt version
4. Write tests for new fields

That's it—the pipeline handles everything else.
