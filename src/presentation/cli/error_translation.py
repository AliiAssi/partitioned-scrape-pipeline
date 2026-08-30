from contextlib import contextmanager

import typer
from pydantic import ValidationError
from rich.console import Console

from src.application.exceptions import PipelineError

console = Console(stderr=True)
INVALID_INPUT_EXIT_CODE = 2

# formatting
@contextmanager
def readable_failures():
    # used so a bad flag or a missing source reads as one line, not a pydantic dump or a traceback
    try:
        yield
    except ValidationError as error:
        for issue in error.errors():
            field = ".".join(str(part) for part in issue["loc"]) or "input"
            console.print(f"[red]invalid input[/red] ({field}): {issue['msg'].removeprefix('Value error, ')}")
        raise typer.Exit(code=INVALID_INPUT_EXIT_CODE) from None
    except (PipelineError, ValueError) as error:
        console.print(f"[red]{type(error).__name__}[/red]: {error}")
        raise typer.Exit(code=INVALID_INPUT_EXIT_CODE) from None
