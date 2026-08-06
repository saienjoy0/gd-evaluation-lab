#!/usr/bin/env python3
"""Validate the Micro Anchor set manifest, coverage, and controlled ladders."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from micro_anchor_contract import anchor_paths, load_json  # noqa: E402
from micro_anchor_set import derive_coverage, validate_manifest  # noqa: E402


def main() -> int:
    validate_manifest(ROOT)
    anchors = [load_json(path) for path in anchor_paths(ROOT)]
    coverage = derive_coverage(anchors)
    complete_dimensions = [
        dimension for dimension, values in coverage.items() if values
    ]
    print("Micro Anchor set OK")
    print(f"Implemented anchors: {len(anchors)} / 35")
    print("Completed ladders: " + ", ".join(complete_dimensions))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
