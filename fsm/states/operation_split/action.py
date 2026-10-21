"""Capability invoked when ``operation_scored`` finds tasks with several strong steps.

The capability asks the local Claude Code to split each task that has more than
one step scored at or above the threshold into one subtask per strong step, and
writes the tasks with their subtasks to the run folder. While ``subtasks.json``
exists in the ``mocks`` folder, that file is used as a mock to avoid spending tokens
during development and tests. Tasks with a single strong step are kept whole.
Whether the scores allow the split is decided by the guards of the previous
states, and the split is verified here against the scores before it is written.
"""

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List, Optional, Union

STATES_PATH: Path = Path(__file__).parents[1]
MOCK_SUBTASKS_PATH: Path = Path(__file__).resolve().parents[3] / "mocks" / "subtasks.json"
TASKS_FILE_NAME: str = "tasks.json"
SUBTASKS_FILE_NAME: str = "subtasks.json"
CLAUDE_INSTRUCTION: str = (
    "Each task below comes with the workflow steps it is closest to (URI and "
    "label). Split every task into exactly one subtask per listed step, each "
    "subtask covering the part of the task that its step performs. Answer with "
    'JSON only: an array with one object per task, each with the keys "id" (the '
    'task id as given) and "subtasks" (an array of objects with the keys "task", '
    '"objective" and "step", the step being the URI it is based on). No prose and '
    "no code fences."
)


def load_module(state_name: str, module_name: str) -> ModuleType:
    """Load a module of another state, which is not importable as a package."""
    module_path: Path = STATES_PATH / state_name / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(f"{state_name}_{module_name}", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load state module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def strong_steps_by_task(scores: List[Any], guard: ModuleType) -> Dict[Any, List[str]]:
    """Map each task id to the URIs of its steps scored at least the threshold."""
    return {
        entry["id"]: [item["uri"] for item in entry["steps"] if item["score"] >= guard.MIN_SCORE]
        for entry in scores
    }


def ask_split(
    tasks: List[Dict[str, Any]],
    strong: Dict[Any, List[str]],
    labels: Dict[str, str],
) -> Optional[Any]:
    """Ask the local Claude Code to split the tasks that have several strong steps."""
    claude: Optional[str] = shutil.which("claude")
    if claude is None:
        return None
    to_split: List[Dict[str, Any]] = [
        {
            "id": task["id"],
            "task": task["task"],
            "objective": task["objective"],
            "steps": [{"uri": uri, "label": labels.get(uri, "")} for uri in strong[task["id"]]],
        }
        for task in tasks
        if len(strong[task["id"]]) > 1
    ]
    request: str = f"{CLAUDE_INSTRUCTION}\n\nTasks:\n{json.dumps(to_split, ensure_ascii=False)}"
    completed: subprocess.CompletedProcess[str] = subprocess.run(
        [claude, "-p", request], capture_output=True, text=True,
    )
    if completed.returncode != 0:
        return None
    try:
        return json.loads(completed.stdout)
    except ValueError:
        return None


def assemble(
    tasks: List[Dict[str, Any]], strong: Dict[Any, List[str]], split: Any,
) -> Optional[List[Dict[str, Any]]]:
    """Nest the subtasks answered by Claude Code inside their tasks."""
    if not isinstance(split, list) or not all(isinstance(entry, dict) for entry in split):
        return None
    subtasks_by_id: Dict[Any, Any] = {entry.get("id"): entry.get("subtasks") for entry in split}
    result: List[Dict[str, Any]] = []
    for task in tasks:
        subtasks: List[Dict[str, Any]] = []
        if len(strong[task["id"]]) > 1:
            answered: Any = subtasks_by_id.get(task["id"])
            if not isinstance(answered, list):
                return None
            for number, item in enumerate(answered, start=1):
                if not isinstance(item, dict):
                    return None
                subtasks.append({"id": f"{task['id']}.{number}", **item})
        result.append({**task, "subtasks": subtasks})
    return result


def is_valid_split(
    result: Any, tasks: List[Dict[str, Any]], strong: Dict[Any, List[str]],
) -> bool:
    """Report whether the nested result keeps the tasks and covers every strong step once."""
    if not isinstance(result, list) or len(result) != len(tasks):
        return False
    for task, entry in zip(tasks, result):
        if not isinstance(entry, dict):
            return False
        if {key: entry.get(key) for key in task} != task:
            return False
        subtasks: Any = entry.get("subtasks")
        expected: List[str] = strong[task["id"]] if len(strong[task["id"]]) > 1 else []
        if not isinstance(subtasks, list) or len(subtasks) != len(expected):
            return False
        for subtask in subtasks:
            if not isinstance(subtask, dict):
                return False
            if not all(isinstance(subtask.get(key), str) and subtask[key].strip()
                       for key in ("task", "objective")):
                return False
        if sorted(subtask.get("step") for subtask in subtasks) != sorted(expected):
            return False
    return True


def action(brief_path: Union[str, Path]) -> bool:
    """Write the tasks with their subtasks into the run folder."""
    run_folder: Path = Path(brief_path).parent
    guard: ModuleType = load_module("operation_scored", "guard")
    scores: Optional[List[Any]] = guard.load_scores(brief_path)
    tasks: Optional[List[Dict[str, Any]]] = load_module("brief_structured", "action").load_tasks(
        run_folder / TASKS_FILE_NAME,
    )
    if scores is None or tasks is None:
        return False
    strong: Dict[Any, List[str]] = strong_steps_by_task(scores, guard)
    if set(strong) != {task["id"] for task in tasks}:
        return False

    result: Any
    if MOCK_SUBTASKS_PATH.is_file():
        try:
            result = json.loads(MOCK_SUBTASKS_PATH.read_text(encoding="utf-8"))
        except ValueError:
            return False
    else:
        labels: Dict[str, str] = load_module("brief_structured", "action").list_steps()
        result = assemble(tasks, strong, ask_split(tasks, strong, labels))
    if not is_valid_split(result, tasks, strong):
        return False

    (run_folder / SUBTASKS_FILE_NAME).write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8",
    )
    return True
