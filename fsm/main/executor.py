"""Execute the marketing operation statechart through Sismic."""

import argparse
import importlib.util
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict, List

from sismic.interpreter import Interpreter
from sismic.io import import_from_yaml

STATE_CHART_PATH: Path = Path(__file__).with_name("marketing-operation.yaml")
BRIEF_GUARD_PATH: Path = Path(__file__).parent / "States" / "Brief Received" / "Guard.py"
BRIEF_FILE_NAME: str = "brief.txt"
DEFAULT_PROMPT_PATH: Path = Path(__file__).resolve().parents[2] / "prompt.txt"


def load_brief_received_guard() -> Callable[[Path], bool]:
    """Load the guard defined for the brief_received state."""
    spec = importlib.util.spec_from_file_location("brief_received_guard", BRIEF_GUARD_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load brief received guard: {BRIEF_GUARD_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.guard


def parse_context_value(raw_value: str) -> Any:
    """Convert a command line value into the boolean, None, or string it denotes."""
    normalized: str = raw_value.strip().lower()
    if normalized in ("true", "false"):
        return normalized == "true"
    if normalized in ("none", "null"):
        return None
    return raw_value


def parse_context(assignments: List[str]) -> Dict[str, Any]:
    """Build the initial context from NAME=VALUE assignments."""
    context: Dict[str, Any] = {}
    for assignment in assignments:
        name, separator, raw_value = assignment.partition("=")
        if not separator:
            raise ValueError(f"Expected NAME=VALUE, got {assignment!r}")
        context[name] = parse_context_value(raw_value)
    return context


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the marketing operation statechart through Sismic.",
    )
    parser.add_argument(
        "events",
        metavar="event",
        nargs="*",
        help="event names dispatched to the statechart, in order",
    )
    parser.add_argument(
        "--context",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="verified fact injected into the statechart context (repeatable)",
    )
    parser.add_argument(
        "--prompt-file",
        type=Path,
        default=DEFAULT_PROMPT_PATH,
        help="marketing prompt file to validate (default: repository prompt.txt)",
    )
    parser.add_argument(
        "--etl-dir",
        type=Path,
        help="run folder holding brief.txt; takes precedence over --prompt-file",
    )
    return parser


def dispatch(interpreter: Interpreter, event_name: str) -> str:
    """Queue one event and report how the statechart reacted to it."""
    interpreter.queue(event_name)
    macro_step = interpreter.execute_once()
    configuration: str = ", ".join(interpreter.configuration)
    if macro_step is None or not macro_step.transitions:
        return f"{event_name}: no transition, still in {configuration}"
    entered: str = ", ".join(macro_step.entered_states) or "-"
    return f"{event_name}: entered {entered}, in {configuration}"


def main() -> None:
    arguments = build_parser().parse_args()
    statechart = import_from_yaml(filepath=STATE_CHART_PATH)
    context = parse_context(arguments.context)
    prompt_file: Path = arguments.etl_dir / BRIEF_FILE_NAME if arguments.etl_dir else arguments.prompt_file
    context["prompt_is_valid"] = partial(load_brief_received_guard(), prompt_file)
    interpreter = Interpreter(statechart, initial_context=context)
    interpreter.execute()
    print(f"initial: {', '.join(interpreter.configuration)}")
    for event_name in arguments.events:
        print(dispatch(interpreter, event_name))
    outcome: str = "final" if interpreter.final else "not final"
    print(f"final: {', '.join(interpreter.configuration) or '-'} ({outcome})")


if __name__ == "__main__":
    main()
