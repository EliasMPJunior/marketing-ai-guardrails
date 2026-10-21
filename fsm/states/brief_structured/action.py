"""Capability invoked when ``brief_structured`` accepts the interpretation.

The capability verifies the tasks listing produced by the interpretation step,
independently of the capability that produced it: the artifact must exist in the
run folder and honor the JSON contract requested from Claude Code. Producing the
listing remains the job of the ``brief_received`` capability.
"""

import json
from pathlib import Path
from typing import Any, List, Union

TASKS_FILE_NAME: str = "tasks.json"
TEXT_KEYS: List[str] = ["task", "objective"]


def is_valid_entry(entry: Any) -> bool:
    """Report whether one entry carries an identifier and both text fields."""
    if not isinstance(entry, dict):
        return False
    if not isinstance(entry.get("id"), (int, str)):
        return False
    return all(
        isinstance(entry.get(key), str) and entry[key].strip() for key in TEXT_KEYS
    )


def action(brief_path: Union[str, Path]) -> bool:
    """Report whether the tasks listing in the run folder honors the contract."""
    tasks_file: Path = Path(brief_path).parent / TASKS_FILE_NAME
    if not tasks_file.is_file():
        return False
    try:
        tasks: Any = json.loads(tasks_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(tasks, list) or not tasks:
        return False
    return all(is_valid_entry(entry) for entry in tasks)
