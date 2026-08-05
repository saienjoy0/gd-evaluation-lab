"""Reusable high/medium/low/system_failure matrix validation."""
from __future__ import annotations

import ast
import json
from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from gd_eval.vertical_slice.loader import load_case
from gd_eval.vertical_slice.runner import compare_oracles, run_full_episode

STATES = ("high", "medium", "low", "system_failure")
NORMAL_STATES = ("high", "medium", "low")
DIMENSIONS = (
    "issue_framing",
    "logical_reasoning",
    "listening_and_response",
    "valuable_contribution",
    "collaboration_and_relationship",
    "decision_and_consensus",
    "process_and_time_management",
)


@dataclass(frozen=True)
class FourStateMatrixConfig:
    title: str
    matrix_id: str
    exercise_id: str
    scenario_version: str
    case_root: Path
    matrix_json: Path
    matrix_markdown: Path
    matrix_schema: Path
    normal_opportunity_summary: dict[str, int]
    system_failure_opportunity_summary: dict[str, int]
    system_failure_ne: tuple[str, ...]
    system_failure_failed_rules: tuple[str, ...]


def score_map(generated: Any) -> dict[str, int | str]:
    return {
        item["dimension"]: item["score"]
        for item in generated.evaluation_result["candidate_dimensions"]
    }


def ai_signature(episode: dict[str, Any]) -> list[tuple[Any, ...]]:
    return [
        (
            message["message_id"],
            message["participant_id"],
            message["text"],
            message["phase"],
            message["move"],
            message["start_ms"],
            message["end_ms"],
            message.get("generation_id"),
        )
        for message in episode["messages"]
        if message["speaker_type"] == "ai"
    ]


def failed_system_rules(generated: Any) -> list[str]:
    return sorted(
        item["rule_id"]
        for item in generated.system_quality["rule_results"]
        if item["outcome"] == "fail"
    )


def semantic_system_quality(generated: Any) -> dict[str, Any]:
    return {
        "status": generated.system_quality["status"],
        "rule_results": generated.system_quality["rule_results"],
        "dimension_scores": generated.system_quality["dimension_scores"],
    }


def runtime_receives_state(runtime: Any) -> bool:
    if is_dataclass(runtime):
        return "state" in {field.name for field in fields(runtime)}
    return hasattr(runtime, "state")


def core_state_literals(root: Path) -> list[str]:
    forbidden = set(STATES)
    hits: list[str] = []
    for path in sorted((root / "gd_eval").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value in forbidden
            ):
                hits.append(f"{path.relative_to(root)}:{node.lineno}:{node.value}")
    return hits


def load_four_states(
    root: Path, config: FourStateMatrixConfig
) -> tuple[dict[str, Any], dict[str, Any]]:
    loaded_by_state: dict[str, Any] = {}
    generated_by_state: dict[str, Any] = {}
    for state in STATES:
        loaded = load_case(config.case_root / state, root)
        if loaded.profile.state != state:
            raise AssertionError(f"CASE_STATE_MISMATCH: {state}")
        generated = run_full_episode(loaded.runtime)
        compare_oracles(generated, loaded.oracle_paths)
        if run_full_episode(loaded.runtime) != generated:
            raise AssertionError(f"NONDETERMINISTIC_CASE_OUTPUT: {state}")
        loaded_by_state[state] = loaded
        generated_by_state[state] = generated
    return loaded_by_state, generated_by_state


def build_matrix(
    root: Path,
    config: FourStateMatrixConfig,
    loaded_by_state: dict[str, Any],
    generated_by_state: dict[str, Any],
) -> dict[str, Any]:
    reference_loaded = loaded_by_state["medium"]
    reference_generated = generated_by_state["medium"]

    cases: list[dict[str, Any]] = []
    for state in STATES:
        loaded = loaded_by_state[state]
        generated = generated_by_state[state]
        scores = score_map(generated)
        ne_dimensions = [
            dimension for dimension in DIMENSIONS if scores[dimension] == "NE"
        ]
        cases.append(
            {
                "state": state,
                "case_id": loaded.profile.case_id,
                "session_id": generated.evaluation_result["session_id"],
                "system_quality": generated.system_quality["status"],
                "failed_system_rules": failed_system_rules(generated),
                "opportunities": generated.opportunity_resolution["summary"],
                "numeric_dimensions": sum(
                    1 for dimension in DIMENSIONS if scores[dimension] != "NE"
                ),
                "ne_dimensions": ne_dimensions,
                "scores": {
                    dimension: scores[dimension] for dimension in DIMENSIONS
                },
            }
        )

    low = score_map(generated_by_state["low"])
    medium = score_map(generated_by_state["medium"])
    system_failure = score_map(generated_by_state["system_failure"])
    unaffected = tuple(
        dimension
        for dimension in DIMENSIONS
        if dimension not in config.system_failure_ne
    )
    return {
        "contract_version": "0.1",
        "matrix_id": config.matrix_id,
        "exercise_id": config.exercise_id,
        "scenario_version": config.scenario_version,
        "runner_version": reference_loaded.profile.versions["runner_version"],
        "states": list(STATES),
        "dimensions": list(DIMENSIONS),
        "controls": {
            "normal_state_ai_messages_equal": all(
                ai_signature(loaded_by_state[state].runtime.episode)
                == ai_signature(reference_loaded.runtime.episode)
                for state in NORMAL_STATES
            ),
            "normal_state_system_quality_equal": all(
                semantic_system_quality(generated_by_state[state])
                == semantic_system_quality(reference_generated)
                for state in NORMAL_STATES
            ),
            "normal_state_opportunity_supply_equal": all(
                generated_by_state[state].opportunity_resolution["items"]
                == reference_generated.opportunity_resolution["items"]
                for state in NORMAL_STATES
            ),
            "runner_receives_state_label": any(
                runtime_receives_state(loaded_by_state[state].runtime)
                for state in STATES
            ),
            "core_state_literals": core_state_literals(root),
        },
        "cases": cases,
        "assertions": {
            "normal_score_order": "high > medium > low",
            "low_all_numeric": all(
                low[dimension] != "NE" for dimension in DIMENSIONS
            ),
            "system_failure_ne_scope": [
                dimension
                for dimension in DIMENSIONS
                if system_failure[dimension] == "NE"
            ],
            "system_failure_unaffected_matches_medium": all(
                system_failure[dimension] == medium[dimension]
                for dimension in unaffected
            ),
            "system_failure_failed_rules": failed_system_rules(
                generated_by_state["system_failure"]
            ),
        },
    }


def render_markdown(
    matrix: dict[str, Any], config: FourStateMatrixConfig
) -> str:
    header = [
        "State",
        "System Quality",
        "Offered",
        "Invalid",
        "Numeric",
        "NE",
        *DIMENSIONS,
    ]
    rows: list[list[str]] = []
    for case in matrix["cases"]:
        rows.append(
            [
                case["state"],
                case["system_quality"],
                str(case["opportunities"]["offered"]),
                str(case["opportunities"]["invalid"]),
                str(case["numeric_dimensions"]),
                ", ".join(case["ne_dimensions"]) or "-",
                *[str(case["scores"][dimension]) for dimension in DIMENSIONS],
            ]
        )

    lines = [
        f"# {config.title}",
        "",
        "| " + " | ".join(header) + " |",
        "|" + "|".join(["---"] * len(header)) + "|",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    lines.extend(
        [
            "",
            "## Cross-state assertions",
            "",
            "- Normal-state AI messages are identical: "
            + str(matrix["controls"]["normal_state_ai_messages_equal"]).lower(),
            "- Normal-state System Quality is identical: "
            + str(
                matrix["controls"]["normal_state_system_quality_equal"]
            ).lower(),
            "- Normal-state opportunity supply is identical: "
            + str(
                matrix["controls"]["normal_state_opportunity_supply_equal"]
            ).lower(),
            "- Runner receives the state label: "
            + str(matrix["controls"]["runner_receives_state_label"]).lower(),
            "- Core state literals: "
            + (", ".join(matrix["controls"]["core_state_literals"]) or "none"),
            "- Score order: " + matrix["assertions"]["normal_score_order"],
            "- Low remains fully numeric: "
            + str(matrix["assertions"]["low_all_numeric"]).lower(),
            "- system_failure NE scope: "
            + ", ".join(matrix["assertions"]["system_failure_ne_scope"]),
            "- system_failure unaffected dimensions match medium: "
            + str(
                matrix["assertions"][
                    "system_failure_unaffected_matches_medium"
                ]
            ).lower(),
            "- system_failure failed rules: "
            + ", ".join(matrix["assertions"]["system_failure_failed_rules"]),
            "",
        ]
    )
    return "\n".join(lines)


def validate_schema(
    matrix: dict[str, Any], config: FourStateMatrixConfig
) -> None:
    raw = json.loads(config.matrix_schema.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(raw)
    errors = sorted(
        Draft202012Validator(
            raw, format_checker=FormatChecker()
        ).iter_errors(matrix),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        raise AssertionError(
            f"MATRIX_SCHEMA_INVALID: {list(first.absolute_path)} {first.message}"
        )


def assert_matrix(
    matrix: dict[str, Any], config: FourStateMatrixConfig
) -> None:
    cases = {case["state"]: case for case in matrix["cases"]}
    if matrix["matrix_id"] != config.matrix_id:
        raise AssertionError("MATRIX_ID_INVALID")
    if matrix["exercise_id"] != config.exercise_id:
        raise AssertionError("EXERCISE_ID_INVALID")
    if matrix["scenario_version"] != config.scenario_version:
        raise AssertionError("SCENARIO_VERSION_INVALID")
    if matrix["states"] != list(STATES):
        raise AssertionError("STATE_ORDER_INVALID")
    if matrix["dimensions"] != list(DIMENSIONS):
        raise AssertionError("DIMENSION_ORDER_INVALID")
    if len({case["case_id"] for case in matrix["cases"]}) != 4:
        raise AssertionError("CASE_ID_COLLISION")
    if len({case["session_id"] for case in matrix["cases"]}) != 4:
        raise AssertionError("SESSION_ID_COLLISION")

    controls = matrix["controls"]
    if not controls["normal_state_ai_messages_equal"]:
        raise AssertionError("NORMAL_AI_MESSAGES_DIFFER")
    if not controls["normal_state_system_quality_equal"]:
        raise AssertionError("NORMAL_SYSTEM_QUALITY_DIFFER")
    if not controls["normal_state_opportunity_supply_equal"]:
        raise AssertionError("NORMAL_OPPORTUNITY_SUPPLY_DIFFER")
    if controls["runner_receives_state_label"]:
        raise AssertionError("RUNNER_RECEIVES_STATE_LABEL")
    if controls["core_state_literals"]:
        raise AssertionError(
            f"CORE_STATE_LITERAL_FOUND: {controls['core_state_literals']}"
        )

    high = cases["high"]["scores"]
    medium = cases["medium"]["scores"]
    low = cases["low"]["scores"]
    for dimension in DIMENSIONS:
        if not int(high[dimension]) > int(medium[dimension]) > int(low[dimension]):
            raise AssertionError(
                "NORMAL_SCORE_ORDER_INVALID: "
                f"{dimension}: {high[dimension]} > "
                f"{medium[dimension]} > {low[dimension]}"
            )

    for state in NORMAL_STATES:
        case = cases[state]
        if case["system_quality"] != "pass":
            raise AssertionError(f"NORMAL_SYSTEM_QUALITY_NOT_PASS: {state}")
        if case["failed_system_rules"]:
            raise AssertionError(f"NORMAL_SYSTEM_RULE_FAILED: {state}")
        if case["numeric_dimensions"] != 7 or case["ne_dimensions"]:
            raise AssertionError(f"NORMAL_NUMERIC_PROFILE_INVALID: {state}")
        if case["opportunities"] != config.normal_opportunity_summary:
            raise AssertionError(f"NORMAL_OPPORTUNITY_PROFILE_INVALID: {state}")

    if not all(
        isinstance(cases["low"]["scores"][dimension], int)
        and cases["low"]["scores"][dimension] <= 2
        for dimension in DIMENSIONS
    ):
        raise AssertionError("LOW_PROFILE_INVALID")

    system_failure = cases["system_failure"]
    if system_failure["system_quality"] != "fail":
        raise AssertionError("SYSTEM_FAILURE_QUALITY_NOT_FAIL")
    if system_failure["failed_system_rules"] != list(
        config.system_failure_failed_rules
    ):
        raise AssertionError("SYSTEM_FAILURE_RULE_SCOPE_INVALID")
    if (
        system_failure["opportunities"]
        != config.system_failure_opportunity_summary
    ):
        raise AssertionError("SYSTEM_FAILURE_OPPORTUNITY_PROFILE_INVALID")
    if system_failure["numeric_dimensions"] != (
        len(DIMENSIONS) - len(config.system_failure_ne)
    ):
        raise AssertionError("SYSTEM_FAILURE_NUMERIC_COUNT_INVALID")
    if system_failure["ne_dimensions"] != list(config.system_failure_ne):
        raise AssertionError("SYSTEM_FAILURE_NE_SCOPE_INVALID")

    unaffected = tuple(
        dimension
        for dimension in DIMENSIONS
        if dimension not in config.system_failure_ne
    )
    for dimension in unaffected:
        if system_failure["scores"][dimension] != medium[dimension]:
            raise AssertionError(
                f"SYSTEM_FAILURE_UNAFFECTED_CHANGED: {dimension}"
            )

    assertions = matrix["assertions"]
    if assertions["normal_score_order"] != "high > medium > low":
        raise AssertionError("NORMAL_SCORE_ASSERTION_INVALID")
    if not assertions["low_all_numeric"]:
        raise AssertionError("LOW_ALL_NUMERIC_ASSERTION_INVALID")
    if assertions["system_failure_ne_scope"] != list(
        config.system_failure_ne
    ):
        raise AssertionError("SYSTEM_FAILURE_NE_ASSERTION_INVALID")
    if not assertions["system_failure_unaffected_matches_medium"]:
        raise AssertionError("SYSTEM_FAILURE_UNAFFECTED_ASSERTION_INVALID")
    if assertions["system_failure_failed_rules"] != list(
        config.system_failure_failed_rules
    ):
        raise AssertionError("SYSTEM_FAILURE_RULE_ASSERTION_INVALID")


def run_four_state_matrix(
    root: Path, config: FourStateMatrixConfig
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    loaded_by_state, generated_by_state = load_four_states(root, config)
    matrix = build_matrix(root, config, loaded_by_state, generated_by_state)
    if build_matrix(root, config, loaded_by_state, generated_by_state) != matrix:
        raise AssertionError("NONDETERMINISTIC_MATRIX_OUTPUT")
    validate_schema(matrix, config)
    assert_matrix(matrix, config)

    actual_json = (
        json.dumps(
            matrix,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )
    if actual_json != config.matrix_json.read_text(encoding="utf-8"):
        raise AssertionError("FOUR_STATE_MATRIX_JSON_MISMATCH")
    if render_markdown(matrix, config) != config.matrix_markdown.read_text(
        encoding="utf-8"
    ):
        raise AssertionError("FOUR_STATE_MATRIX_MARKDOWN_MISMATCH")
    return matrix, loaded_by_state, generated_by_state
