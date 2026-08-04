"""Build and validate the dependency-aware full-Episode Manifest."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from .models import CaseProfile, GeneratedArtifacts, RuntimeCase


class ManifestError(ValueError):
    pass


def canonical_json_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _repo_path(runtime: RuntimeCase, path: Path) -> str:
    return path.resolve().relative_to(runtime.repo_root.resolve()).as_posix()


def _entry(path: str, content: bytes, role: str, depends_on: Iterable[str] = ()) -> dict[str, Any]:
    return {
        "path": path,
        "sha256": sha256_bytes(content),
        "role": role,
        "depends_on": list(depends_on),
    }


def _validate_dag(entries: list[dict[str, Any]]) -> None:
    by_path = {entry["path"]: entry for entry in entries}
    if len(by_path) != len(entries):
        raise ManifestError("MANIFEST_DUPLICATE_PATH")
    for entry in entries:
        for dependency in entry["depends_on"]:
            if dependency not in by_path:
                raise ManifestError(
                    f"MANIFEST_DEPENDENCY_MISSING: {entry['path']} -> {dependency}"
                )
            if entry["role"] == "generated" and by_path[dependency]["role"] == "test_oracle":
                raise ManifestError(
                    f"TEST_ORACLE_GENERATION_DEPENDENCY: {entry['path']} -> {dependency}"
                )

    evaluation = by_path.get("evaluation-result.json")
    if evaluation and "feedback.json" in evaluation["depends_on"]:
        raise ManifestError("EVALUATION_DEPENDS_ON_FEEDBACK")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(path: str) -> None:
        if path in visiting:
            raise ManifestError(f"MANIFEST_CYCLE: {path}")
        if path in visited:
            return
        visiting.add(path)
        for dependency in by_path[path]["depends_on"]:
            visit(dependency)
        visiting.remove(path)
        visited.add(path)

    for path in by_path:
        visit(path)


def build_manifest(
    profile: CaseProfile,
    runtime: RuntimeCase,
    generated: GeneratedArtifacts,
    oracle_paths: dict[str, Path] | Any,
) -> dict[str, Any]:
    case_path = runtime.case_dir / "case.json"
    scenario_path = _repo_path(runtime, runtime.scenario_path)
    episode_path = _repo_path(runtime, runtime.episode_path)
    candidate_rubric_path = _repo_path(runtime, runtime.candidate_rubric_path)
    ai_quality_rubric_path = _repo_path(runtime, runtime.ai_quality_rubric_path)
    rater_paths = [_repo_path(runtime, path) for path in runtime.rater_sheet_paths]
    adjudication_path = _repo_path(runtime, runtime.adjudication_path)

    entries: list[dict[str, Any]] = [
        _entry(_repo_path(runtime, case_path), case_path.read_bytes(), "source"),
        _entry(scenario_path, runtime.scenario_path.read_bytes(), "source"),
        _entry(episode_path, runtime.episode_path.read_bytes(), "source"),
        _entry(candidate_rubric_path, runtime.candidate_rubric_path.read_bytes(), "source"),
        _entry(ai_quality_rubric_path, runtime.ai_quality_rubric_path.read_bytes(), "source"),
    ]
    for path, repo_path in zip(runtime.rater_sheet_paths, rater_paths, strict=True):
        entries.append(
            _entry(repo_path, path.read_bytes(), "human_authored", [episode_path])
        )
    entries.append(
        _entry(
            adjudication_path,
            runtime.adjudication_path.read_bytes(),
            "human_authored",
            [episode_path, *rater_paths],
        )
    )

    generated_map = generated.as_mapping()
    generated_bytes = {
        path: canonical_json_bytes(content) for path, content in generated_map.items()
    }
    entries.extend(
        [
            _entry(
                "deterministic-rule-result.json",
                generated_bytes["deterministic-rule-result.json"],
                "generated",
                [scenario_path, episode_path],
            ),
            _entry(
                "system-quality-result.json",
                generated_bytes["system-quality-result.json"],
                "generated",
                [scenario_path, episode_path, "deterministic-rule-result.json"],
            ),
            _entry(
                "opportunity-resolution.json",
                generated_bytes["opportunity-resolution.json"],
                "generated",
                [scenario_path, episode_path, "system-quality-result.json"],
            ),
            _entry(
                "evaluation-result.json",
                generated_bytes["evaluation-result.json"],
                "generated",
                [
                    episode_path,
                    candidate_rubric_path,
                    ai_quality_rubric_path,
                    *rater_paths,
                    adjudication_path,
                    "system-quality-result.json",
                    "opportunity-resolution.json",
                ],
            ),
            _entry(
                "feedback.json",
                generated_bytes["feedback.json"],
                "generated",
                ["evaluation-result.json"],
            ),
        ]
    )

    for name, path in sorted(dict(oracle_paths).items()):
        entries.append(
            _entry(
                f"test-oracles/{name}/{_repo_path(runtime, path)}",
                path.read_bytes(),
                "test_oracle",
            )
        )

    _validate_dag(entries)
    return {
        "contract_version": "0.1",
        "manifest_version": "full-episode-manifest-v0.1",
        "case_id": profile.case_id,
        "exercise_id": profile.exercise_id,
        "state": profile.state,
        "runner_version": profile.versions["runner_version"],
        "artifacts": entries,
    }


def validate_manifest(manifest: dict[str, Any]) -> None:
    _validate_dag(manifest["artifacts"])
