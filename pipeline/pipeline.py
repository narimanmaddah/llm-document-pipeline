from dataclasses import dataclass
from typing import Dict, Any
from pathlib import Path
import os

from .config import PipelineConfig
from .quality_gate.classifier import QualityClassifier
from .ocr.extractor import OCRExtractor
from .ocr.language_detection import LanguageDetector
from .pii.detector import PIIDetector
from .pii.redactor import PIIRedactor
from .extraction.llm_extractor import LLMExtractor
from .extraction.confidence import ConfidenceScorer
from .validation.schema import SchemaValidator
from .validation.routing import ReviewRouter


@dataclass
class PipelineResult:
    extracted_fields: Dict[str, Any]
    quality_score: float
    language: str
    requires_review: bool
    pii_detected: bool
    confidence_summary: Dict[str, Any]
    raw_text: str = None  # Not persisted to disk, only in-memory


class DocumentPipeline:
    def __init__(self, config: PipelineConfig):
        self.config = config

        # Initialize components
        self.quality_classifier = QualityClassifier()
        self.ocr_extractor = OCRExtractor()
        self.language_detector = LanguageDetector()
        self.pii_detector = PIIDetector()
        self.pii_redactor = PIIRedactor(config.pii.audit_log_path)
        self.llm_extractor = LLMExtractor(model=config.llm.model, temperature=config.llm.temperature)
        self.confidence_scorer = ConfidenceScorer()
        self.schema_validator = SchemaValidator()
        self.review_router = ReviewRouter(
            field_review_threshold=config.confidence.field_review_threshold,
            document_auto_approve=config.confidence.document_auto_approve,
        )

    def process(self, document_path: str) -> PipelineResult:
        """Process a document through the full pipeline."""
        document_path = str(document_path)

        # Stage 1: Quality Gate
        quality_score = self.quality_classifier.score(document_path)
        if quality_score < self.config.quality_gate.route_to_review_below:
            return PipelineResult(
                extracted_fields={},
                quality_score=quality_score,
                language="unknown",
                requires_review=True,
                pii_detected=False,
                confidence_summary={},
                raw_text="Document quality too low for processing.",
            )

        # Stage 2: OCR + Language Detection
        raw_text = self.ocr_extractor.extract_text(document_path)
        language = self.language_detector.detect_language(raw_text)

        # Stage 3: PII Detection & Redaction
        redacted_text, pii_metadata = self.pii_redactor.redact(raw_text, self.config.pii.entities_to_detect)

        # Stage 4: LLM Extraction (on redacted text to prevent exposing PII via LLM)
        try:
            extracted_fields = self.llm_extractor.extract(redacted_text, self.config.llm.prompt_version)
        except Exception as e:
            # If LLM fails, return with review required
            extracted_fields = {}

        # Stage 5: Confidence Scoring
        scored_fields = self.confidence_scorer.score_document(extracted_fields)

        # Stage 6: Validation & Routing
        is_valid, validated = self.schema_validator.validate(extracted_fields)
        requires_review = self.review_router.should_route_for_review(
            scored_fields, quality_score, pii_metadata["pii_detected"]
        )
        confidence_summary = self.review_router.get_confidence_summary(scored_fields)

        return PipelineResult(
            extracted_fields=scored_fields,
            quality_score=quality_score,
            language=language,
            requires_review=requires_review,
            pii_detected=pii_metadata["pii_detected"],
            confidence_summary=confidence_summary,
            raw_text=None,  # Never return raw text due to PII risk
        )

    def process_batch(self, document_paths: list[str]) -> list[PipelineResult]:
        """Process multiple documents."""
        results = []
        for path in document_paths:
            try:
                result = self.process(path)
                results.append(result)
            except Exception as e:
                # Log error and continue
                print(f"Error processing {path}: {e}")
                results.append(
                    PipelineResult(
                        extracted_fields={},
                        quality_score=0.0,
                        language="unknown",
                        requires_review=True,
                        pii_detected=False,
                        confidence_summary={},
                    )
                )
        return results
