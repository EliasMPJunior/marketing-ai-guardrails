"""Execute the marketing operation statechart through Sismic."""

import argparse
from pathlib import Path
from typing import Any, Dict, List

from sismic.interpreter import Interpreter
from sismic.io import import_from_yaml

STATE_CHART_PATH: Path = Path(__file__).with_name("marketing-operation.yaml")


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
    interpreter = Interpreter(statechart, initial_context=parse_context(arguments.context))
    interpreter.execute()
    print(f"initial: {', '.join(interpreter.configuration)}")
    for event_name in arguments.events:
        print(dispatch(interpreter, event_name))
    outcome: str = "final" if interpreter.final else "not final"
    print(f"final: {', '.join(interpreter.configuration) or '-'} ({outcome})")


if __name__ == "__main__":
    main()
