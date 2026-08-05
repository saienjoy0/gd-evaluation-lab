#!/usr/bin/env python3
"""Run one full-Episode case through the generic deterministic pipeline."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gd_eval.vertical_slice.loader import load_case  # noqa: E402
from gd_eval.vertical_slice.manifest import (  # noqa: E402
    build_manifest,
    canonical_json_bytes,
    validate_manifest,
)
from gd_eval.vertical_slice.runner import (  # noqa: E402
    compare_oracles,
    run_full_episode,
    write_generated,
)


def _schema(instance: dict, filename: str) -> None:
    schema = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        raise ValueError(
            f"SCHEMA_INVALID: {filename}: {list(first.absolute_path)} {first.message}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    loaded = load_case(args.case_dir, ROOT)
    generated = run_full_episode(loaded.runtime)
    repeated = run_full_episode(loaded.runtime)
    if generated != repeated:
        raise ValueError("NONDETERMINISTIC_OUTPUT")
    manifest = build_manifest(
        loaded.profile, loaded.runtime, generated, loaded.oracle_paths
    )
    repeated_manifest = build_manifest(
        loaded.profile, loaded.runtime, repeated, loaded.oracle_paths
    )
    if manifest != repeated_manifest:
        raise ValueError("NONDETERMINISTIC_MANIFEST")
    validate_manifest(manifest)

    _schema(generated.deterministic_rules, "deterministic-rule-result-v0.1.schema.json")
    _schema(generated.system_quality, "system-quality-result-v0.1.schema.json")
    _schema(generated.opportunity_resolution, "opportunity-resolution-v0.1.schema.json")
    _schema(generated.evaluation_result, "evaluation-result-v0.1.schema.json")
    _schema(manifest, "full-episode-manifest-v0.1.schema.json")

    if args.check:
        compare_oracles(generated, loaded.oracle_paths)
        print("Generic full-Episode runner v0.1 OK")
        print(f"Case: {loaded.profile.case_id}")
        print(f"Rules: {len(generated.deterministic_rules['rule_results'])}")
        print(f"Opportunities: {len(generated.opportunity_resolution['items'])}")
        print("Golden replay: exact")
        print("Manifest DAG: valid")
        return

    output_dir = (args.output_dir or args.case_dir / "generated").resolve()
    write_generated(output_dir, generated)
    (output_dir / "manifest.json").write_bytes(canonical_json_bytes(manifest))
    print(output_dir)


if __name__ == "__main__":
    main()
