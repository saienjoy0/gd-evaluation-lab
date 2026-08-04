from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_DIMENSIONS = {
    "issue_framing",
    "logical_reasoning",
    "listening_and_response",
    "valuable_contribution",
    "collaboration_and_relationship",
    "decision_and_consensus",
    "process_and_time_management",
}
AI_DIMENSIONS = {
    "goal_progression",
    "responsiveness",
    "user_agency",
    "role_believability",
    "discussion_coherence",
    "novelty_and_repetition",
    "consensus_quality",
    "natural_pacing",
}
FILES = [
    "docs/EVALUATION_PURPOSE.md",
    "docs/COMPETENCY_MODEL.md",
    "docs/RUBRIC_DESIGN.md",
    "docs/EVALUATION_CONTRACT_V0.1.md",
    "rubrics/candidate-behavior/v0.1.json",
    "rubrics/ai-participant/v0.1.json",
    "schemas/scenario-v0.1.schema.json",
    "schemas/episode-v0.1.schema.json",
    "schemas/annotation-v0.1.schema.json",
    "schemas/evaluation-result-v0.1.schema.json",
    "fixtures/scenarios/market-entry-001.json",
    "fixtures/episodes/example-episode-v0.1.json",
    "fixtures/annotations/example-human-annotation-v0.1.json",
    "fixtures/results/example-evaluation-result-v0.1.json",
]


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main() -> int:
    errors: list[str] = []

    for path in FILES:
        if not (ROOT / path).is_file():
            errors.append(f"missing: {path}")

    if errors:
        print("\n".join(errors))
        return 1

    candidate = load("rubrics/candidate-behavior/v0.1.json")
    dimensions = candidate.get("dimensions", [])
    if {item.get("id") for item in dimensions} != CANDIDATE_DIMENSIONS:
        errors.append("candidate dimension set mismatch")
    for item in dimensions:
        if set(item.get("anchors", {})) != {"1", "2", "3", "4"}:
            errors.append(f"{item.get('id')}: anchors must be 1-4")
        if len(item.get("questions", [])) < 4:
            errors.append(f"{item.get('id')}: four questions required")
        if item.get("evidence_policy", {}).get("minimum_for_score_4") != 2:
            errors.append(f"{item.get('id')}: score 4 requires two evidence items")

    ai = load("rubrics/ai-participant/v0.1.json")
    if {item.get("id") for item in ai.get("dimensions", [])} != AI_DIMENSIONS:
        errors.append("AI dimension set mismatch")
    if not any(rule.get("severity") == "critical" for rule in ai.get("deterministic_rules", [])):
        errors.append("critical AI quality rule required")

    for path in [item for item in FILES if item.startswith("schemas/")]:
        schema = load(path)
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            errors.append(f"{path}: schema version mismatch")

    scenario = load("fixtures/scenarios/market-entry-001.json")
    if set(scenario.get("evaluation_opportunities", {})) != CANDIDATE_DIMENSIONS:
        errors.append("scenario must declare seven evaluation opportunities")
    if not scenario.get("instance_rubrics"):
        errors.append("scenario requires instance rubrics")

    episode = load("fixtures/episodes/example-episode-v0.1.json")
    message_ids = [item.get("message_id") for item in episode.get("messages", [])]
    if len(message_ids) != len(set(message_ids)):
        errors.append("episode message IDs must be unique")

    result = load("fixtures/results/example-evaluation-result-v0.1.json")
    if {item.get("dimension") for item in result.get("candidate_dimensions", [])} != CANDIDATE_DIMENSIONS:
        errors.append("result must contain seven dimensions")
    for item in result.get("candidate_dimensions", []):
        score = item.get("score")
        evidence = set(item.get("evidence_message_ids", []))
        if score == "NE" and not item.get("not_evaluable_reason"):
            errors.append(f"{item.get('dimension')}: NE reason required")
        if score != "NE" and not evidence:
            errors.append(f"{item.get('dimension')}: evidence required")
        if score == 4 and len(evidence) < 2:
            errors.append(f"{item.get('dimension')}: two evidence messages required")

    if errors:
        print("Evaluation contract validation failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1

    print("Evaluation contract v0.1 OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
