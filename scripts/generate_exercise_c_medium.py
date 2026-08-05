#!/usr/bin/env python3
"""Generate deterministic goldens for Exercise C medium."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CASE_DIR = ROOT / "fixtures/calibration/full-episodes/time-boxed-decision/medium"

from gd_eval.vertical_slice.loader import load_case  # noqa: E402
from gd_eval.vertical_slice.runner import run_full_episode, write_generated  # noqa: E402


def main() -> None:
    loaded = load_case(CASE_DIR, ROOT)
    generated = run_full_episode(loaded.runtime)
    write_generated(CASE_DIR, generated)

    feedback = CASE_DIR / "feedback.json"
    if feedback.exists():
        feedback.replace(CASE_DIR / "expected-feedback.json")
    print("Generated Exercise C medium goldens")


if __name__ == "__main__":
    main()
