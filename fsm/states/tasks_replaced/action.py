"""Capability invoked when ``operation_split`` has nested the subtasks in their tasks.

The capability replaces ``tasks.json`` in the run folder with the new list of
tasks: each split task is substituted by its subtasks and the tasks that were not
split are kept as they are. The previous listing stays recoverable from
``subtasks.json``, which holds the original tasks with their subtasks.
"""

import importlib.util
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

STATES_PATH: Path = Path(__file__).parents[1]
TASKS_FILE_NAME: str = "tasks.json"
SUBTASKS_FILE_NAME: str = "subtasks.json"
TASK_KEYS: List[str] = ["id", "task", "objective"]


def load_tasks_contract() -> Any:
    """Load the brief_structured module that defines the tasks listing contract."""
    module_path: Path = STATES_PATH / "brief_structured" / "action.py"
    spec = importlib.util.spec_from_file_location("brief_structured_action", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load state module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def flatten(nested: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Replace each task that has subtasks by them, keeping the other tasks whole."""
    tasks: List[Dict[str, Any]] = []
    for entry in nested:
        if entry["subtasks"]:
            tasks.extend({key: subtask[key] for key in TASK_KEYS} for subtask in entry["subtasks"])
        else:
            tasks.append({key: value for key, value in entry.items() if key != "subtasks"})
    return tasks


def action(brief_path: Union[str, Path]) -> bool:
    """Replace the tasks listing in the run folder by the list with the subtasks."""
    run_folder: Path = Path(brief_path).parent
    contract: Any = load_tasks_contract()
    try:
        nested: Any = json.loads((run_folder / SUBTASKS_FILE_NAME).read_text(encoding="utf-8"))
        tasks: List[Dict[str, Any]] = flatten(nested)
    except (OSError, ValueError, KeyError, TypeError):
        return False
    if not tasks or not all(contract.is_valid_entry(task) for task in tasks):
        return False
    if len({task["id"] for task in tasks}) != len(tasks):
        return False
    (run_folder / TASKS_FILE_NAME).write_text(
        json.dumps(tasks, indent=2, ensure_ascii=False), encoding="utf-8",
    )
    return True
