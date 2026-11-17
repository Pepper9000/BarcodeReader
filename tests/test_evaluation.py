"""
Automated tests for evaluation harness and research question benchmarks.
"""

from pathlib import Path
import json
import pytest

from scripts.evaluate_recovery import (
    DEFAULT_DATASET_DIR,
    build_synthetic_benchmark_dataset,
    evaluate_dataset,
)

BASE_DIR = Path(__file__).resolve().parent.parent
GENERATED_DIR = BASE_DIR / "generated"


def test_evaluation_dataset_manifest_and_provenance():
    """Verify evaluation dataset exists, paired with ground truth, and marked synthetic."""
    manifest_file = DEFAULT_DATASET_DIR / "manifest.json"
    assert manifest_file.exists(), f"Missing dataset manifest: {manifest_file}"

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert len(manifest) >= 42

    for entry in manifest:
        assert "filename" in entry
        assert "ground_truth_code" in entry
        assert len(entry["ground_truth_code"]) == 13
        assert entry["synthetic"] is True
        assert "damage_type" in entry
        assert (DEFAULT_DATASET_DIR / "images" / entry["filename"]).exists()


def test_evaluation_metrics_and_zero_false_identifications():
    """Verify evaluation runs and preserves zero false product identifications."""
    report = evaluate_dataset(DEFAULT_DATASET_DIR)

    assert report["total_test_cases"] >= 42

    std = report["standard_decoder"]
    rec = report["recovery_pipeline"]

    # Zero false identifications requirement
    assert std["false_identifications"] == 0
    assert rec["false_identifications"] == 0
    assert rec["false_identification_rate"] == 0.0

    # Recovery pipeline must improve over standard decoder
    assert rec["exact_matches"] > std["exact_matches"]
    assert rec["exact_recovery_rate"] > std["exact_recovery_rate"]

    # Abstentions must be recorded
    assert rec["abstentions"] > 0

    # Severe unrecoverable damage must abstain (zero false guesses)
    severe_stats = report["breakdown_by_damage_type"]["severe_unrecoverable"]["recovered"]
    assert severe_stats["false_id"] == 0
    assert severe_stats["exact"] == 0
    assert severe_stats["abstain"] == severe_stats["total"]
