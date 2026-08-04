"""Generic deterministic full-Episode evaluation runner."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from gd_eval.feedback.builder import build_feedback
from gd_eval.opportunities.resolver import resolve_opportunities
from gd_eval.quality.system_quality import build_system_quality
from gd_eval.results.evaluation_result import build_evaluation_result
from gd_eval.rules.registry import evaluate_deterministic_rules

from .manifest import canonical_json_bytes
from .models import GeneratedArtifacts, RuntimeCase


class RunnerError(ValueError):
    pass


def transcript_hash(messages: list[dict[str, Any]]) -> str:
    payload = json.dumps(
        messages,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validate_runtime(runtime: RuntimeCase) -> None:
    if runtime.episode.get("scenario_id") != runtime.scenario.get("scenario_id"):
        raise RunnerError("VERSION_MISMATCH: scenario_id")
    if runtime.episode.get("scenario_version") != runtime.scenario.get("version"):
        raise RunnerError("VERSION_MISMATCH: scenario_version")
    participants = {
        item.get("participant_id"): item for item in runtime.episode.get("participants", [])
    }
    target = participants.get(runtime.target_participant_id)
    if target is None or target.get("speaker_type") != "user":
        raise RunnerError("TARGET_PARTICIPANT_MISSING")
    annotators = [sheet.get("annotator_id") for sheet in runtime.rater_sheets]
    if len(annotators) != 2 or len(set(annotators)) != 2:
        raise RunnerError("DUPLICATE_RATER")
    if runtime.adjudication.get("adjudicator_id") in set(annotators):
        raise RunnerError("ADJUDICATOR_OVERLAP")
    expected = transcript_hash(runtime.episode["messages"])
    if runtime.episode.get("transcript_hash") != expected:
        raise RunnerError("TRANSCRIPT_HASH_MISMATCH")


def run_full_episode(runtime: RuntimeCase) -> GeneratedArtifacts:
    _validate_runtime(runtime)
    deterministic = evaluate_deterministic_rules(
        runtime.scenario,
        runtime.episode,
        runtime.target_participant_id,
        runtime.versions["deterministic_evaluator_version"],
    )
    system_quality = build_system_quality(
        runtime.scenario,
        runtime.episode,
        deterministic,
        runtime.target_participant_id,
        runtime.versions["deterministic_evaluator_version"],
    )
    opportunities = resolve_opportunities(
        runtime.scenario,
        runtime.episode,
        system_quality,
        runtime.target_participant_id,
        runtime.versions["opportunity_resolver_version"],
    )
    evaluation = build_evaluation_result(
        runtime.exercise_id,
        runtime.episode,
        runtime.target_participant_id,
        runtime.candidate_rubric,
        runtime.ai_quality_rubric,
        system_quality,
        opportunities,
        runtime.rater_sheets,
        runtime.adjudication,
        runtime.versions["deterministic_evaluator_version"],
    )
    feedback = build_feedback(runtime.case_id, evaluation, runtime.candidate_rubric)
    return GeneratedArtifacts(
        deterministic_rules=deterministic,
        system_quality=system_quality,
        opportunity_resolution=opportunities,
        evaluation_result=evaluation,
        feedback=feedback,
    )


def write_generated(output_dir: Path, generated: GeneratedArtifacts) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in generated.as_mapping().items():
        (output_dir / filename).write_bytes(canonical_json_bytes(content))


def compare_oracles(
    generated: GeneratedArtifacts, oracle_paths: dict[str, Path] | Any
) -> None:
    generated_by_key = {
        "deterministic_rules": generated.deterministic_rules,
        "system_quality": generated.system_quality,
        "opportunity_resolution": generated.opportunity_resolution,
        "evaluation_result": generated.evaluation_result,
        "feedback": generated.feedback,
    }
    for key, expected_path in dict(oracle_paths).items():
        if key not in generated_by_key:
            continue
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        if generated_by_key[key] != expected:
            raise RunnerError(f"GOLDEN_MISMATCH: {key}")
