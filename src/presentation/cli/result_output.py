import json

import typer

from src.application.dto.base.partition_result_dto import RunResultDTO


def emit_summary(result: RunResultDTO) -> None:
    # stdout is a json stream, so the closing summary has to be one parseable line like every log
    # line before it. a pretty-printed dict here breaks piping the whole run through jq.
    typer.echo(json.dumps(result.as_log_fields()))
