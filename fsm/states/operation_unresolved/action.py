"""Capability invoked when ``operation_scored`` finds no single strong step per task.

The capability shows an alert on screen, with Textual when the terminal is
interactive, explaining which tasks the scores could not resolve and that the
demand can be integrated into the human tasks workflow. It does not decide
anything about the demand: the outcome is left to people.
"""

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, List, Optional, Union

from rich.console import Console
from rich.panel import Panel
from textual.app import App, ComposeResult
from textual.widgets import Footer, Static

GUARD_PATH: Path = Path(__file__).parents[1] / "operation_scored" / "guard.py"
TITLE: str = "Human attention required"

console = Console()


def load_guard() -> Any:
    """Load the score threshold guard of the operation_scored state."""
    spec = importlib.util.spec_from_file_location("operation_scored_guard", GUARD_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load guard module: {GUARD_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_message(brief_path: Union[str, Path]) -> str:
    """Explain why the scores could not single out one step for every task."""
    guard: Any = load_guard()
    scores: Optional[List[Any]] = guard.load_scores(brief_path)
    if scores is None:
        reason: str = f"The step scores in {guard.SCORES_FILE_NAME} are missing or unreadable."
    else:
        unresolved: List[str] = [
            f"  - task {entry['id']}: {guard.count_strong_steps(entry)} step(s)"
            for entry in scores
            if guard.count_strong_steps(entry) != 1
        ]
        reason = (
            f"Every task needs exactly one step scored {guard.MIN_SCORE} or more, "
            "but these tasks have a different count:\n" + "\n".join(unresolved)
        )
    return (
        "The operation could not be matched automatically to the workflow.\n\n"
        f"{reason}\n\n"
        "This demand can be integrated into the human tasks workflow."
    )


class AlertApp(App[None]):
    """Single-screen alert, closed by any of the bindings below."""

    BINDINGS = [("q", "quit", "Close"), ("enter", "quit", "Close"), ("escape", "quit", "Close")]

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message: str = message

    def compose(self) -> ComposeResult:
        yield Static(
            Panel(self.message, title=TITLE, border_style="yellow", padding=(1, 3)),
        )
        yield Footer()


def action(brief_path: Union[str, Path]) -> bool:
    """Show the alert for the run folder of the given brief."""
    message: str = build_message(brief_path)
    interactive: bool = (
        sys.stdin.isatty()
        and sys.stdout.isatty()
        and os.environ.get("TERM") not in (None, "dumb")
    )
    if interactive:
        AlertApp(message).run(inline=True)
    else:
        console.print(Panel(message, title=TITLE, border_style="yellow", padding=(1, 3)))
    return True
