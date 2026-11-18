from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "release_gate.py"
SPEC = importlib.util.spec_from_file_location("klod_release_gate", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


def valid_payload(count: int = 12, score: float = 8.8) -> dict:
    return {
        "confirmations": [
            {
                "id": index,
                "name": f"Gate {index}",
                "status": "pass",
                "score": score,
                "evidence": ["https://github.com/japaguimarassi-create/J/actions/runs/44362763954"],
            }
            for index in range(1, 13)
        ]
    }


def test_release_gate_accepts_twelve_valid_evidence_records() -> None:
    errors, average = GATE.evaluate_payload(valid_payload(), 12)
    assert errors == []
    assert average == pytest.approx(8.8)


def test_release_gate_rejects_missing_confirmation_evidence() -> None:
    payload = valid_payload()
    payload["confirmations"][3]["evidence"] = []
    errors, _ = GATE.evaluate_payload(payload, 12)
    assert any("evidence references are missing" in error for error in errors)


@pytest.mark.parametrize("score", [float("nan"), float("inf"), -1.0, 10.1, True])
def test_release_gate_rejects_invalid_scores(score) -> None:
    payload = valid_payload()
    payload["confirmations"][0]["score"] = score
    errors, _ = GATE.evaluate_payload(payload, 12)
    assert any("score" in error for error in errors)


def test_release_gate_rejects_non_repository_evidence_links() -> None:
    payload = valid_payload()
    payload["confirmations"][0]["evidence"] = ["https://example.com/claimed-proof"]
    errors, _ = GATE.evaluate_payload(payload, 12)
    assert any("evidence must link to this repository" in error for error in errors)


def test_release_gate_enforces_both_score_thresholds() -> None:
    payload = valid_payload(score=8.0)
    errors, average = GATE.evaluate_payload(payload, 12)
    assert average == pytest.approx(8.0)
    assert any("Average" in error for error in errors)


def test_current_release_record_blocks_android_candidate_until_real_dependencies_pass():
    evidence_path = SCRIPT.parents[1] / "docs" / "release-evidence.json"
    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    errors, _ = GATE.evaluate_payload(payload, 11)
    assert any(error.startswith("5. ") for error in errors)
    assert any(error.startswith("7. ") for error in errors)
