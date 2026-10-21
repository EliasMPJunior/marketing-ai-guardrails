"""Capability invoked when ``brief_structured`` accepts the interpretation.

The capability first verifies the tasks listing produced by the interpretation
step, independently of the capability that produced it: the artifact must exist
in the run folder and honor the JSON contract requested from Claude Code.
It then lists every ``p-plan:Step`` of the activities ontology and asks the local
Claude Code to score how close each of three steps is to each task, writing the
scores to the run folder; while ``step_scores.json`` exists at the project root,
that file is used as a mock to avoid spending tokens during development and
tests. Producing the tasks listing remains the job of the ``brief_received``
capability.
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from rdflib import Graph

ONTOLOGY_PATH: Path = Path(__file__).resolve().parents[3] / "ontology" / "activities.ttl"
MOCK_SCORES_PATH: Path = Path(__file__).resolve().parents[3] / "step_scores.json"
TASKS_FILE_NAME: str = "tasks.json"
SCORES_FILE_NAME: str = "step_scores.json"
TEXT_KEYS: List[str] = ["task", "objective"]
STEPS_PER_TASK: int = 3
STEPS_QUERY: str = """
PREFIX p-plan: <http://purl.org/net/p-plan#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?step ?label WHERE {
    ?step a p-plan:Step .
    OPTIONAL { ?step rdfs:label ?label }
}
ORDER BY ?step
"""
CLAUDE_INSTRUCTION: str = (
    "Below are a list of tasks and a list of workflow steps (URI and label). For "
    f"each task, choose exactly {STEPS_PER_TASK} distinct steps and give each a "
    "proximity score between 0 and 1 (1 means the step is exactly the work the "
    "task describes). Answer with JSON only: an array with one object per task, "
    'each with the keys "id" (the task id as given) and "steps" (an array of '
    f'{STEPS_PER_TASK} objects with the keys "uri" and "score"). Use only URIs '
    "from the list. No prose and no code fences."
)


def is_valid_entry(entry: Any) -> bool:
    """Report whether one entry carries an identifier and both text fields."""
    if not isinstance(entry, dict):
        return False
    if not isinstance(entry.get("id"), (int, str)):
        return False
    return all(
        isinstance(entry.get(key), str) and entry[key].strip() for key in TEXT_KEYS
    )


def load_tasks(tasks_file: Path) -> Optional[List[Dict[str, Any]]]:
    """Return the tasks listing when it honors the contract, otherwise None."""
    if not tasks_file.is_file():
        return None
    try:
        tasks: Any = json.loads(tasks_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(tasks, list) or not tasks:
        return None
    if not all(is_valid_entry(entry) for entry in tasks):
        return None
    return tasks


def list_steps() -> Dict[str, str]:
    """Return the URI and label of every p-plan:Step in the activities ontology."""
    graph: Graph = Graph()
    graph.parse(ONTOLOGY_PATH, format="turtle")
    return {str(row.step): str(row.label or "") for row in graph.query(STEPS_QUERY)}


def ask_scores(tasks: List[Dict[str, Any]], steps: Dict[str, str]) -> Optional[Any]:
    """Ask the local Claude Code to score the proximity between tasks and steps."""
    if MOCK_SCORES_PATH.is_file():
        try:
            mock: Any = json.loads(MOCK_SCORES_PATH.read_text(encoding="utf-8"))
            by_id: Dict[Any, Any] = {entry["id"]: entry for entry in mock}
        except (OSError, ValueError, KeyError, TypeError):
            return None
        # The mock holds scores for every task id used in the demos; keep the current ones.
        return [by_id[task["id"]] for task in tasks if task["id"] in by_id]
    claude: Optional[str] = shutil.which("claude")
    if claude is None:
        return None
    steps_listing: List[Dict[str, str]] = [
        {"uri": uri, "label": label} for uri, label in steps.items()
    ]
    request: str = (
        f"{CLAUDE_INSTRUCTION}\n\nTasks:\n{json.dumps(tasks, ensure_ascii=False)}"
        f"\n\nSteps:\n{json.dumps(steps_listing, ensure_ascii=False)}"
    )
    completed: subprocess.CompletedProcess[str] = subprocess.run(
        [claude, "-p", request], capture_output=True, text=True,
    )
    if completed.returncode != 0:
        return None
    try:
        return json.loads(completed.stdout)
    except ValueError:
        return None


def is_valid_score(item: Any, steps: Dict[str, str]) -> bool:
    """Report whether one step score names an ontology step and a 0 to 1 score."""
    if not isinstance(item, dict) or item.get("uri") not in steps:
        return False
    score: Any = item.get("score")
    return isinstance(score, (int, float)) and not isinstance(score, bool) and 0 <= score <= 1


def are_valid_scores(
    scores: Any, tasks: List[Dict[str, Any]], steps: Dict[str, str],
) -> bool:
    """Report whether the scores cover every task with distinct ontology steps."""
    if not isinstance(scores, list) or len(scores) != len(tasks):
        return False
    if [entry.get("id") if isinstance(entry, dict) else None for entry in scores] != [
        task["id"] for task in tasks
    ]:
        return False
    for entry in scores:
        items: Any = entry.get("steps")
        if not isinstance(items, list) or len(items) != STEPS_PER_TASK:
            return False
        if not all(is_valid_score(item, steps) for item in items):
            return False
        if len({item["uri"] for item in items}) != STEPS_PER_TASK:
            return False
    return True


def action(brief_path: Union[str, Path]) -> bool:
    """Verify the tasks listing and write the step proximity scores beside it."""
    run_folder: Path = Path(brief_path).parent
    tasks: Optional[List[Dict[str, Any]]] = load_tasks(run_folder / TASKS_FILE_NAME)
    if tasks is None:
        return False
    steps: Dict[str, str] = list_steps()
    scores: Optional[Any] = ask_scores(tasks, steps)
    if not are_valid_scores(scores, tasks, steps):
        return False
    (run_folder / SCORES_FILE_NAME).write_text(
        json.dumps(scores, indent=2, ensure_ascii=False), encoding="utf-8",
    )
    return True
