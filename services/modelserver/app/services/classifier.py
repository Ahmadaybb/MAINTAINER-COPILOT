from __future__ import annotations

import os
from dataclasses import dataclass, field

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from app.domain.classify import ClassifyResponse, IssueLabel
from app.domain.errors import BootValidationError
from app.infra.artifact import ModelArtifact


@dataclass(slots=True)
class ClassifierService:
    artifact: ModelArtifact
    confidence_margin: float = 0.55
    tokenizer: object = field(init=False)
    model: object = field(init=False)
    id2label: dict[int, IssueLabel] = field(init=False)

    def __post_init__(self) -> None:
        if not self.artifact.artifact_dir:
            raise BootValidationError("A local transformer export is required to load the classifier.")
        self.confidence_margin = float(os.getenv("CLASSIFIER_CONFIDENCE_MARGIN", str(self.confidence_margin)))
        self.tokenizer = AutoTokenizer.from_pretrained(self.artifact.artifact_dir)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.artifact.artifact_dir)
        self.model.eval()
        self.id2label = _id2label(self.artifact.model_card)

    def classify(self, text: str) -> ClassifyResponse:
        inputs = self.tokenizer(text, truncation=True, max_length=256, return_tensors="pt")
        with torch.no_grad():
            logits = self.model(**inputs).logits[0]
            probs = torch.softmax(logits, dim=0)
            confidence, label_id = torch.max(probs, dim=0)
        label = self.id2label[int(label_id.item())]
        confidence_value = float(confidence.item())
        return ClassifyResponse(
            label=label,
            confidence=confidence_value,
            low_confidence=confidence_value < self.confidence_margin,
            model_name=self.artifact.model_name,
            model_version=self.artifact.version,
            sha256=self.artifact.sha256,
        )


def _id2label(model_card: dict[str, object]) -> dict[int, IssueLabel]:
    raw = model_card.get("id2label") or {"0": "bug", "1": "feature", "2": "docs", "3": "question"}
    if not isinstance(raw, dict):
        raise BootValidationError("Model card id2label is invalid.")
    return {int(key): str(value) for key, value in raw.items()}  # type: ignore[return-value]
