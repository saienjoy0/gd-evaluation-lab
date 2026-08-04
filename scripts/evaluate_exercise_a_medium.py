#!/usr/bin/env python3
"""Compatibility entry point for the generic full-Episode runner."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gd_eval.vertical_slice.loader import load_case  # noqa: E402
from gd_eval.vertical_slice.runner import run_full_episode  # noqa: E402

CASE_DIR = ROOT / "fixtures/calibration/full-episodes/ambiguous-structure/medium"


def build(repo: Path = ROOT) -> dict:
    loaded = load_case(
        repo / "fixtures/calibration/full-episodes/ambiguous-structure/medium",
        repo,
    )
    generated = run_full_episode(loaded.runtime)
    return {
        "deterministic_rules": generated.deterministic_rules,
        "system_quality": generated.system_quality,
        "opportunity_resolution": generated.opportunity_resolution,
        "evaluation_result": generated.evaluation_result,
        "feedback": generated.feedback,
    }


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2, sort_keys=True))
