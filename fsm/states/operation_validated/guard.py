"""Objective checks for the ``operation_validated`` state.

These checks read the step scores written to the run folder by the
``brief_structured`` capability. They only count scores against a threshold;
they do not decide whether a high score means the step truly fits the task.
"""

import json
from pathlib import Path
from typing import Any, List, Optional, Union

SCORES_FILE_NAME: str = "step_scores.json"
MIN_SCORE: float = 0.8


def count_strong_steps(entry: Any) -> int:
    """Count the steps of one task whose score is at least MIN_SCORE."""
    return sum(1 for item in entry["steps"] if item["score"] >= MIN_SCORE)


def load_scores(brief_path: Union[str, Path]) -> Optional[List[Any]]:
    """Return the scores listing from the run folder, or None when unusable."""
    scores_file: Path = Path(brief_path).parent / SCORES_FILE_NAME
    try:
        scores: Any = json.loads(scores_file.read_text(encoding="utf-8"))
        if not isinstance(scores, list) or not scores:
            return None
        for entry in scores:
            count_strong_steps(entry)
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return scores


def every_task_has_strong_step(brief_path: Union[str, Path]) -> bool:
    """Report whether every task has at least one step scored MIN_SCORE or more."""
    scores: Optional[List[Any]] = load_scores(brief_path)
    return scores is not None and all(count_strong_steps(entry) >= 1 for entry in scores)


def every_task_has_single_strong_step(brief_path: Union[str, Path]) -> bool:
    """Report whether every task has exactly one step scored MIN_SCORE or more."""
    scores: Optional[List[Any]] = load_scores(brief_path)
    return scores is not None and all(count_strong_steps(entry) == 1 for entry in scores)
