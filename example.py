#!/usr/bin/env python3
"""Simple example showing the pipeline in action."""

import os
from pathlib import Path
from pipeline import DocumentPipeline, PipelineConfig

# Load config
config = PipelineConfig.from_yaml("config/pipeline_config.yaml")

# Initialize pipeline
pipeline = DocumentPipeline(config)

# Example: Process a single test document
# For this example, we'll create a simple test image
print("LLM Document Pipeline - Example")
print("=" * 50)

print(
    f"""
Configuration loaded:
  - Quality gate threshold: {config.quality_gate.min_quality_score}
  - LLM model: {config.llm.model}
  - Confidence threshold: {config.confidence.field_review_threshold}
  - PII entities to detect: {', '.join(config.pii.entities_to_detect)}

To process documents, call:
  result = pipeline.process("path/to/document.pdf")

The result will include:
  - extracted_fields: Dict of fields with confidence scores
  - quality_score: 0-1 quality metric
  - language: Detected language
  - requires_review: Boolean flag for human review
  - pii_detected: Was PII found and redacted
  - confidence_summary: Min/avg/max confidence across fields
"""
)

# Show PII detection example
print("PII Detection Example:")
print("-" * 50)
test_text = """
Invoice from John Smith (john.smith@example.com)
Phone: (555) 123-4567
Tax ID: 12-3456789
IBAN: DE89370400440532013000
"""

from pipeline.pii.redactor import PIIRedactor

redactor = PIIRedactor()
redacted, metadata = redactor.redact(test_text, config.pii.entities_to_detect)

print(f"Original:\n{test_text}")
print(f"\nRedacted:\n{redacted}")
print(f"\nPII Metadata: {metadata}")
