#!/usr/bin/env python3
"""Validate every committed Micro Anchor v0.1 fixture and rating contract."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from micro_anchor_contract import (  # noqa: E402
    anchor_paths,
    load_json,
    validate_anchor,
    validate_schema,
)


def validate_rating_contract() -> None:
    schema = ROOT / "schemas" / "micro-anchor-rating-v0.1.schema.json"
    numeric = {
        "contract_version": "0.1",
        "rating_version": "micro-anchor-rating-v0.1",
        "blind_anchor_id": "blind-001",
        "rater_id": "rater-example",
        "rubric_version": "candidate-behavior-v0.1",
        "target_dimension": "issue_framing",
        "opportunity_status": "sufficient",
        "selected_evidence_message_ids": ["m003"],
        "assigned_score": 3,
        "not_evaluable_reason": None,
        "confidence": 0.8,
        "notes": "",
    }
    not_evaluable = {
        **numeric,
        "blind_anchor_id": "blind-002",
        "opportunity_status": "invalid",
        "selected_evidence_message_ids": [],
        "assigned_score": "NE",
        "not_evaluable_reason": "AI_QUALITY_FAILURE",
    }
    validate_schema(
        numeric,
        schema,
        code="MICRO_ANCHOR_RATING_SCHEMA_INVALID",
    )
    validate_schema(
        not_evaluable,
        schema,
        code="MICRO_ANCHOR_RATING_SCHEMA_INVALID",
    )


def main() -> int:
    paths = anchor_paths(ROOT)
    if not paths:
        raise AssertionError("MICRO_ANCHOR_FIXTURES_MISSING")
    for path in paths:
        validate_anchor(load_json(path), path, ROOT)
    validate_rating_contract()
    print("Micro Anchor contract OK")
    print(f"Validated anchors: {len(paths)}")
    print("Blind rating contract: numeric and NE examples valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
