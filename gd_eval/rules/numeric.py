"""Generic deterministic numeric-constraint checks."""
from __future__ import annotations

from typing import Any


def _check_value(value: Any, check: dict[str, Any]) -> bool:
    if "equals" in check and value != check["equals"]:
        return False
    if "maximum" in check and (value is None or value > check["maximum"]):
        return False
    if "minimum" in check and (value is None or value < check["minimum"]):
        return False
    return True


def numeric_constraint_preserved(
    scenario: dict[str, Any], episode: dict[str, Any], params: dict[str, Any]
) -> dict[str, Any]:
    del scenario
    checks = list(params.get("checks", []))
    if not checks and params.get("field"):
        legacy_check: dict[str, Any] = {"field": params["field"]}
        for operator in ("equals", "maximum", "minimum"):
            if operator in params:
                legacy_check[operator] = params[operator]
        checks = [legacy_check]

    event_name = params.get("event")
    matching = [
        event
        for event in episode.get("events", [])
        if (event_name is None or event.get("event") == event_name)
        and all(check.get("field") in event for check in checks)
    ]
    valid = [
        event
        for event in matching
        if checks
        and all(
            _check_value(event.get(check["field"]), check)
            for check in checks
        )
    ]
    return {
        "ok": bool(valid),
        "evidence_message_ids": [
            event["message_id"] for event in valid if event.get("message_id")
        ],
        "evidence_event_ids": [event["event_id"] for event in valid],
        "detail": "数値制約が保たれている。",
    }
