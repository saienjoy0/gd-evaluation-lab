from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
REQUIRED_MARKERS = ("---", "## Observations", "## Relations")


def validate(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    if not text.startswith("---\n"):
        errors.append("missing YAML frontmatter")
    for marker in REQUIRED_MARKERS[1:]:
        if marker not in text:
            errors.append(f"missing {marker}")
    if "permalink:" not in text:
        errors.append("missing permalink")
    return errors


def main() -> int:
    failures: list[tuple[Path, list[str]]] = []
    for path in sorted(KNOWLEDGE.rglob("*.md")):
        errors = validate(path)
        if errors:
            failures.append((path.relative_to(ROOT), errors))

    if failures:
        for path, errors in failures:
            print(f"{path}: {', '.join(errors)}")
        return 1

    print("Knowledge contract OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
