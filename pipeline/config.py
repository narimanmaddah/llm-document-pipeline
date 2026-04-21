from dataclasses import dataclass, field
from typing import List
import yaml


@dataclass
class QualityGateConfig:
    min_quality_score: float = 0.75
    route_to_review_below: float = 0.60


@dataclass
class LLMConfig:
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    prompt_version: str = "v1_invoice"
    max_retries: int = 3
    temperature: float = 0.1


@dataclass
class ConfidenceConfig:
    field_review_threshold: float = 0.80
    document_auto_approve: float = 0.90


@dataclass
class PIIConfig:
    entities_to_detect: List[str] = field(default_factory=lambda: ["PERSON", "EMAIL", "PHONE"])
    redaction_mode: str = "replace"
    audit_log_path: str = "logs/pii_audit.jsonl"


@dataclass
class MonitoringConfig:
    metrics_export: str = "stdout"
    drift_window_days: int = 7


@dataclass
class PipelineConfig:
    quality_gate: QualityGateConfig = field(default_factory=QualityGateConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    confidence: ConfidenceConfig = field(default_factory=ConfidenceConfig)
    pii: PIIConfig = field(default_factory=PIIConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)

    @classmethod
    def from_yaml(cls, path: str) -> "PipelineConfig":
        with open(path) as f:
            data = yaml.safe_load(f)

        return cls(
            quality_gate=QualityGateConfig(**data.get("quality_gate", {})),
            llm=LLMConfig(**data.get("llm", {})),
            confidence=ConfidenceConfig(**data.get("confidence", {})),
            pii=PIIConfig(**data.get("pii", {})),
            monitoring=MonitoringConfig(**data.get("monitoring", {})),
        )
