"""Typed data structures for deterministic full-Episode evaluation."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

JsonObject = dict[str, Any]


@dataclass(frozen=True)
class CaseProfile:
    contract_version: str
    case_id: str
    exercise_id: str
    state: str
    scenario_path: str
    target_participant_id: str
    episode_path: str
    candidate_rubric_path: str
    ai_quality_rubric_path: str
    rater_sheet_paths: tuple[str, ...]
    adjudication_path: str
    versions: Mapping[str, str]
    test_oracles: Mapping[str, str]


@dataclass(frozen=True)
class RuntimeCase:
    """Generation inputs only. Test oracles and state are intentionally absent."""

    repo_root: Path
    case_dir: Path
    case_id: str
    exercise_id: str
    target_participant_id: str
    scenario_path: Path
    episode_path: Path
    candidate_rubric_path: Path
    ai_quality_rubric_path: Path
    rater_sheet_paths: tuple[Path, ...]
    adjudication_path: Path
    scenario: JsonObject
    episode: JsonObject
    candidate_rubric: JsonObject
    ai_quality_rubric: JsonObject
    rater_sheets: tuple[JsonObject, ...]
    adjudication: JsonObject
    versions: Mapping[str, str]


@dataclass(frozen=True)
class LoadedCase:
    profile: CaseProfile
    runtime: RuntimeCase
    oracle_paths: Mapping[str, Path]


@dataclass(frozen=True)
class GeneratedArtifacts:
    deterministic_rules: JsonObject
    system_quality: JsonObject
    opportunity_resolution: JsonObject
    evaluation_result: JsonObject
    feedback: JsonObject

    def as_mapping(self) -> dict[str, JsonObject]:
        return {
            "deterministic-rule-result.json": self.deterministic_rules,
            "system-quality-result.json": self.system_quality,
            "opportunity-resolution.json": self.opportunity_resolution,
            "evaluation-result.json": self.evaluation_result,
            "feedback.json": self.feedback,
        }
