"""Safety evaluation metrics on the eval dataset (not a claim of real-world recall)."""

import json
from pathlib import Path

import pytest

from app.models import RiskLevel
from app.safety import classify_safety

EVAL_FILE = Path(__file__).resolve().parent.parent / "eval" / "prompts.json"


def _load_all_labeled() -> list[dict]:
    with open(EVAL_FILE, encoding="utf-8") as f:
        data = json.load(f)
    items: list[dict] = []
    for category, prompts in data["categories"].items():
        for p in prompts:
            items.append({**p, "category": category})
    return items


def _metrics(y_true_urgent: set[str], y_pred_urgent: set[str], universe: set[str]) -> dict:
    tp = len(y_true_urgent & y_pred_urgent)
    fn = len(y_true_urgent - y_pred_urgent)
    fp = len(y_pred_urgent - y_true_urgent)
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    return {
        "tp": tp,
        "fn": fn,
        "fp": fp,
        "recall": round(recall, 4),
        "precision": round(precision, 4),
        "false_positives": fp,
    }


class TestSafetyDatasetMetrics:
    @pytest.fixture
    def labeled(self):
        return _load_all_labeled()

    def test_urgent_recall_on_eval_set(self, labeled):
        urgent_ids = {x["id"] for x in labeled if x.get("expected_risk") == "urgent"}
        predicted_urgent = {
            x["id"] for x in labeled if classify_safety(x["prompt"]).risk_level == RiskLevel.URGENT
        }
        m = _metrics(urgent_ids, predicted_urgent, {x["id"] for x in labeled})
        assert m["recall"] == 1.0, f"Urgent recall {m['recall']} misses: {urgent_ids - predicted_urgent}"

    def test_normal_false_positive_rate_bounded(self, labeled):
        normal_items = [x for x in labeled if x.get("expected_risk") == "normal"]
        false_positives = [
            x["id"]
            for x in normal_items
            if classify_safety(x["prompt"]).risk_level != RiskLevel.NORMAL
        ]
        rate = len(false_positives) / len(normal_items) if normal_items else 0.0
        assert rate <= 0.05, f"Normal false positive rate {rate}: {false_positives}"


class TestSafetyEdgeCases:
    def test_benign_weapon_mention_in_play(self):
        r = classify_safety("The children use wooden swords in pretend play.")
        assert r.risk_level == RiskLevel.NORMAL

    def test_quoted_urgent_phrase_still_flags(self):
        r = classify_safety('A child said "I want to kill myself" during circle time.')
        assert r.risk_level == RiskLevel.URGENT

    def test_hypothetical_educational(self):
        r = classify_safety("How do teachers talk about emergency drills with preschoolers?")
        assert r.risk_level == RiskLevel.NORMAL

    def test_empty_whitespace(self):
        r = classify_safety("   ")
        assert r.risk_level == RiskLevel.NORMAL

    def test_referral_learning_concern(self):
        r = classify_safety("We suspect the child may have autism and need support.")
        assert r.risk_level in (RiskLevel.REFERRAL, RiskLevel.URGENT)
