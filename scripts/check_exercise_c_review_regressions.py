#!/usr/bin/env python3
"""Regression checks for the blocking findings from the PR #15 review."""
from __future__ import annotations

import copy
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CASE_DIR = ROOT / "fixtures/calibration/full-episodes/time-boxed-decision/medium"

from gd_eval.quality.system_quality import build_system_quality  # noqa: E402
from gd_eval.rules.registry import evaluate_deterministic_rules  # noqa: E402
from gd_eval.vertical_slice.loader import (  # noqa: E402
    CaseLoadError,
    load_case,
    validate_adjudication_trigger_reasons,
)


def _message(episode: dict, message_id: str) -> dict:
    return next(
        item for item in episode["messages"] if item["message_id"] == message_id
    )


def _event(episode: dict, event_id: str) -> dict:
    return next(
        item for item in episode["events"] if item["event_id"] == event_id
    )


def _outcomes(result: dict) -> dict[str, str]:
    return {
        item["rule_id"]: item["outcome"]
        for item in result["rule_results"]
    }


def _deterministic_for(runtime) -> dict:
    return evaluate_deterministic_rules(
        runtime.scenario,
        runtime.episode,
        runtime.target_participant_id,
        runtime.versions["deterministic_evaluator_version"],
    )


def _quality_for(runtime) -> dict:
    deterministic = _deterministic_for(runtime)
    return build_system_quality(
        runtime.scenario,
        runtime.episode,
        deterministic,
        runtime.target_participant_id,
        runtime.versions["deterministic_evaluator_version"],
    )


def main() -> None:
    loaded = load_case(CASE_DIR, ROOT)

    if loaded.runtime.adjudication["trigger_reasons"] != [
        "RANDOM_CALIBRATION_SAMPLE"
    ]:
        raise AssertionError("EXERCISE_C_ADJUDICATION_REASON_NOT_REPAIRED")

    false_gap = copy.deepcopy(loaded.runtime.adjudication)
    false_gap["trigger_reasons"].append("SCORE_GAP_TWO_OR_MORE")
    try:
        validate_adjudication_trigger_reasons(false_gap)
    except CaseLoadError as exc:
        if "SCORE_GAP_TWO_OR_MORE" not in str(exc):
            raise AssertionError(
                f"WRONG_ADJUDICATION_TRIGGER_FAILURE: {exc}"
            ) from exc
    else:
        raise AssertionError("FALSE_SCORE_GAP_TRIGGER_NOT_REJECTED")

    late_message_episode = copy.deepcopy(loaded.runtime.episode)
    _message(late_message_episode, "m027").update(
        start_ms=580000,
        end_ms=590000,
    )
    late_message_runtime = replace(
        loaded.runtime,
        episode=late_message_episode,
    )
    if _outcomes(_deterministic_for(late_message_runtime)).get("C-R02") != "fail":
        raise AssertionError("C_R02_EVENT_MESSAGE_TIME_MISMATCH_NOT_CAUGHT")

    fake_risk_episode = copy.deepcopy(loaded.runtime.episode)
    _message(fake_risk_episode, "m015")["move"] = "propose_decision"
    fake_risk_episode["events"].append(
        {
            "event_id": "ev_fake_early_risk",
            "event": "PRIVATE_CONCERN_REVEALED",
            "timestamp_ms": 100000,
            "participant_id": "ai_c_operations",
            "message_id": "missing_message",
            "late_risk": True,
            "concern": "個人端末から社内演習環境へ接続できない",
        }
    )
    fake_risk_runtime = replace(
        loaded.runtime,
        episode=fake_risk_episode,
    )
    if _outcomes(_quality_for(fake_risk_runtime)).get("C-PROH-01") != "fail":
        raise AssertionError("C_PROH_01_FAKE_RISK_BYPASS_NOT_CAUGHT")

    revision_episode = copy.deepcopy(loaded.runtime.episode)
    _event(revision_episode, "ev_revision").update(before_message_id="m026")
    revision_runtime = replace(loaded.runtime, episode=revision_episode)
    if _outcomes(_deterministic_for(revision_runtime)).get("C-R04") != "fail":
        raise AssertionError("C_R04_INVALID_BEFORE_MESSAGE_NOT_CAUGHT")

    print("Exercise C PR #15 review regressions OK")
    print("Adjudication trigger semantics: fail closed")
    print("C-R02 event/message provenance: fail closed")
    print("C-R04 before/risk/after ordering: fail closed")
    print("C-PROH-01 fake-risk bypass: fail closed")


if __name__ == "__main__":
    main()
