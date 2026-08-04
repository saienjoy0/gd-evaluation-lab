"""Load and cross-check a full-Episode case without exposing test oracles."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .models import CaseProfile, LoadedCase, RuntimeCase


class CaseLoadError(ValueError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CaseLoadError(f"CASE_PATH_MISSING: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CaseLoadError(f"CASE_JSON_INVALID: {path}: {exc}") from exc


def _validate_schema(instance: dict[str, Any], schema_path: Path) -> None:
    schema = load_json(schema_path)
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        raise CaseLoadError(
            f"CASE_SCHEMA_INVALID: {list(first.absolute_path)}: {first.message}"
        )


def _safe_path(repo_root: Path, case_dir: Path, raw: str) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise CaseLoadError(f"UNSAFE_CASE_PATH: {raw}")
    case_relative = (case_dir / candidate).resolve()
    repo_relative = (repo_root / candidate).resolve()
    repo_root_resolved = repo_root.resolve()
    options = [case_relative, repo_relative]
    for option in options:
        try:
            option.relative_to(repo_root_resolved)
        except ValueError:
            continue
        if option.exists():
            return option
    preferred = case_relative if len(candidate.parts) == 1 else repo_relative
    try:
        preferred.relative_to(repo_root_resolved)
    except ValueError as exc:
        raise CaseLoadError(f"UNSAFE_CASE_PATH: {raw}") from exc
    return preferred


def _parse_profile(raw: dict[str, Any]) -> CaseProfile:
    human = raw["human_inputs"]
    return CaseProfile(
        contract_version=raw["contract_version"],
        case_id=raw["case_id"],
        exercise_id=raw["exercise_id"],
        state=raw["state"],
        scenario_path=raw["scenario_path"],
        target_participant_id=raw["target_participant_id"],
        episode_path=raw["episode_path"],
        candidate_rubric_path=raw["candidate_rubric_path"],
        ai_quality_rubric_path=raw["ai_quality_rubric_path"],
        rater_sheet_paths=tuple(human["rater_sheet_paths"]),
        adjudication_path=human["adjudication_path"],
        versions=dict(raw["versions"]),
        test_oracles=dict(raw.get("test_oracles", {})),
    )


def _cross_validate(runtime: RuntimeCase) -> None:
    scenario = runtime.scenario
    episode = runtime.episode
    adjudication = runtime.adjudication
    sheets = runtime.rater_sheets

    if runtime.exercise_id != scenario.get("scenario_id"):
        raise CaseLoadError("EXERCISE_ID_MISMATCH")
    if episode.get("scenario_id") != scenario.get("scenario_id"):
        raise CaseLoadError("VERSION_MISMATCH: scenario_id")
    if episode.get("scenario_version") != scenario.get("version"):
        raise CaseLoadError("VERSION_MISMATCH: scenario_version")

    participants = {
        participant.get("participant_id"): participant
        for participant in episode.get("participants", [])
    }
    target = participants.get(runtime.target_participant_id)
    if target is None or target.get("speaker_type") != "user":
        raise CaseLoadError("TARGET_PARTICIPANT_MISSING")

    if len(sheets) != 2:
        raise CaseLoadError("RATER_COUNT_INVALID: exactly two independent raters required")
    annotators = [sheet.get("annotator_id") for sheet in sheets]
    if len(set(annotators)) != len(annotators):
        raise CaseLoadError("DUPLICATE_RATER")
    if any(sheet.get("evaluation_stage") != "independent" for sheet in sheets):
        raise CaseLoadError("RATER_NOT_INDEPENDENT")
    if any(sheet.get("episode_id") != episode.get("session_id") for sheet in sheets):
        raise CaseLoadError("RATER_EPISODE_MISMATCH")
    if any(sheet.get("scenario_id") != scenario.get("scenario_id") for sheet in sheets):
        raise CaseLoadError("RATER_SCENARIO_MISMATCH")

    sheet_ids = [sheet.get("sheet_id") for sheet in sheets]
    if adjudication.get("rater_sheet_ids") != sheet_ids:
        raise CaseLoadError("ADJUDICATION_RATER_SET_MISMATCH")
    if adjudication.get("adjudicator_id") in set(annotators):
        raise CaseLoadError("ADJUDICATOR_OVERLAP")
    if adjudication.get("episode_id") != episode.get("session_id"):
        raise CaseLoadError("ADJUDICATION_EPISODE_MISMATCH")
    if adjudication.get("scenario_id") != scenario.get("scenario_id"):
        raise CaseLoadError("ADJUDICATION_SCENARIO_MISMATCH")


def load_case(case_dir: Path, repo_root: Path | None = None) -> LoadedCase:
    case_dir = case_dir.resolve()
    repo_root = (repo_root or Path(__file__).resolve().parents[2]).resolve()
    profile_path = case_dir / "case.json"
    raw_profile = load_json(profile_path)
    _validate_schema(raw_profile, repo_root / "schemas/full-episode-case-v0.1.schema.json")
    profile = _parse_profile(raw_profile)

    scenario_path = _safe_path(repo_root, case_dir, profile.scenario_path)
    episode_path = _safe_path(repo_root, case_dir, profile.episode_path)
    candidate_rubric_path = _safe_path(repo_root, case_dir, profile.candidate_rubric_path)
    ai_quality_rubric_path = _safe_path(repo_root, case_dir, profile.ai_quality_rubric_path)
    rater_paths = tuple(
        _safe_path(repo_root, case_dir, path) for path in profile.rater_sheet_paths
    )
    adjudication_path = _safe_path(repo_root, case_dir, profile.adjudication_path)

    runtime = RuntimeCase(
        repo_root=repo_root,
        case_dir=case_dir,
        case_id=profile.case_id,
        exercise_id=profile.exercise_id,
        target_participant_id=profile.target_participant_id,
        scenario_path=scenario_path,
        episode_path=episode_path,
        candidate_rubric_path=candidate_rubric_path,
        ai_quality_rubric_path=ai_quality_rubric_path,
        rater_sheet_paths=rater_paths,
        adjudication_path=adjudication_path,
        scenario=load_json(scenario_path),
        episode=load_json(episode_path),
        candidate_rubric=load_json(candidate_rubric_path),
        ai_quality_rubric=load_json(ai_quality_rubric_path),
        rater_sheets=tuple(load_json(path) for path in rater_paths),
        adjudication=load_json(adjudication_path),
        versions=profile.versions,
    )
    _cross_validate(runtime)
    oracle_paths = {
        name: _safe_path(repo_root, case_dir, path)
        for name, path in profile.test_oracles.items()
    }
    return LoadedCase(profile=profile, runtime=runtime, oracle_paths=oracle_paths)
