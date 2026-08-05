#!/usr/bin/env python3
"""Materialize the authored Exercise C medium Episode from its compressed source."""
from __future__ import annotations

import base64
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = ROOT / "fixtures/calibration/full-episodes/time-boxed-decision/medium"
SOURCE = CASE_DIR / "episode.json.gz.b64"
OUTPUT = CASE_DIR / "episode.json"
EXPECTED_FILE_SHA256 = "6f6b2c09780854dda922e7fecb219968ece805639ac41944175dad37a3bb04ef"
EXPECTED_TRANSCRIPT_HASH = (
    "84ddd149a37e39fff933357d1a60e75ca1dde9afaa73724a8ebdf55c1b9ca1f6"
)


def main() -> None:
    encoded = SOURCE.read_text(encoding="utf-8").strip()
    raw = gzip.decompress(base64.b64decode(encoded, validate=True))
    actual_sha256 = hashlib.sha256(raw).hexdigest()
    if actual_sha256 != EXPECTED_FILE_SHA256:
        raise AssertionError(
            f"EXERCISE_C_EPISODE_PAYLOAD_HASH_MISMATCH: {actual_sha256}"
        )

    episode = json.loads(raw)
    if episode.get("transcript_hash") != EXPECTED_TRANSCRIPT_HASH:
        raise AssertionError("EXERCISE_C_TRANSCRIPT_HASH_MISMATCH")

    OUTPUT.write_bytes(raw)
    print(f"Materialized {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
