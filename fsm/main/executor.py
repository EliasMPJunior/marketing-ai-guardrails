"""Execute the marketing operation statechart through Sismic."""

import argparse
import importlib.util
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict

from sismic.interpreter import Interpreter
from sismic.io import import_from_yaml

STATE_CHART_PATH: Path = Path(__file__).with_name("marketing_operation.yaml")
STATES_PATH: Path = Path(__file__).parents[1] / "states"
BRIEF_FILE_NAME: str = "brief.txt"


def load_state_callable(state_name: str, module_name: str, attribute: str) -> Callable[[Path], Any]:
    """Load one callable (guard or capability) defined by a state module."""
    module_path: Path = STATES_PATH / state_name / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(f"{state_name}_{module_name}", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load state module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, attribute)


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
        "--etl-dir",
        type=Path,
        required=True,
        help="run folder holding brief.txt",
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
    prompt_file: Path = arguments.etl_dir / BRIEF_FILE_NAME
    context: Dict[str, Any] = {
        "check_prompt": partial(load_state_callable("brief_received", "guard", "guard"), prompt_file),
        "interpret_brief": partial(load_state_callable("brief_received", "action", "action"), prompt_file),
        "score_tasks": partial(load_state_callable("brief_structured", "action", "action"), prompt_file),
    }
    interpreter = Interpreter(statechart, initial_context=context)
    interpreter.execute()
    print(f"initial: {', '.join(interpreter.configuration)}")
    for event_name in arguments.events:
        print(dispatch(interpreter, event_name))
    outcome: str = "final" if interpreter.final else "not final"
    print(f"final: {', '.join(interpreter.configuration) or '-'} ({outcome})")


if __name__ == "__main__":
    main()
