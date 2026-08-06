#!/usr/bin/env python3
"""Export a deterministic blind Micro Anchor pack without expected answers."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_KEYS = {
    "anchor_id",
    "target_score",
    "expected_evidence_message_ids",
    "expected_not_evaluable_reason",
    "rationale",
    "boundary_note",
    "approval_status",
    "author",
    "reviewer",
    "status",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def anchor_paths(root: Path) -> list[Path]:
    return sorted(
        path
        for path in (root / "fixtures" / "anchors").glob("*/*.json")
        if path.parent.name != "blind"
        and path.name != "anchor-set-v0.1.json"
    )


def blind_sort_key(anchor_id: str) -> str:
    return hashlib.sha256(anchor_id.encode("utf-8")).hexdigest()


def build_blind_pack(root: Path) -> dict[str, Any]:
    anchors = [load_json(path) for path in anchor_paths(root)]
    anchors.sort(key=lambda item: blind_sort_key(item["anchor_id"]))
    entries: list[dict[str, Any]] = []
    for index, anchor in enumerate(anchors, start=1):
        opportunity = {
            key: value
            for key, value in anchor["opportunity_description"].items()
            if key != "status"
        }
        entries.append(
            {
                "blind_anchor_id": f"blind-{index:03d}",
                "rubric_version": anchor["rubric_version"],
                "target_dimension": anchor["target_dimension"],
                "scenario_context": anchor["scenario_context"],
                "opportunity_description": opportunity,
                "participants": anchor["participants"],
                "micro_episode": anchor["micro_episode"],
            }
        )
    return {
        "contract_version": "0.1",
        "blind_pack_version": "micro-anchor-blind-pack-v0.1",
        "anchor_set_version": "micro-anchor-set-v0.1",
        "rubric_version": "candidate-behavior-v0.1",
        "entry_count": len(entries),
        "entries": entries,
    }


def find_forbidden_keys(value: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in FORBIDDEN_KEYS:
                hits.append(child_path)
            hits.extend(find_forbidden_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(find_forbidden_keys(child, f"{path}[{index}]"))
    return hits


def serialize(pack: dict[str, Any]) -> str:
    return json.dumps(pack, ensure_ascii=False, indent=2) + "\n"


def build_oracle(pack: dict[str, Any], rendered: str) -> dict[str, Any]:
    return {
        "contract_version": pack["contract_version"],
        "blind_pack_version": pack["blind_pack_version"],
        "anchor_set_version": pack["anchor_set_version"],
        "rubric_version": pack["rubric_version"],
        "entry_count": pack["entry_count"],
        "sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    pack = build_blind_pack(ROOT)
    hits = find_forbidden_keys(pack)
    if hits:
        raise AssertionError(f"BLIND_PACK_EXPECTED_VALUE_LEAK: {hits}")

    rendered = serialize(pack)
    oracle = (
        ROOT
        / "fixtures"
        / "anchors"
        / "blind"
        / "issue-framing-v0.1.json"
    )
    if args.check:
        if load_json(oracle) != build_oracle(pack, rendered):
            raise AssertionError("BLIND_PACK_ORACLE_MISMATCH")
        print("Micro Anchor blind pack OK")
        print(f"Blind entries: {pack['entry_count']}")
        return 0

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
