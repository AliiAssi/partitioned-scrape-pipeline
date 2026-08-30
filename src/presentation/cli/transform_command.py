import typer

from src.core.providers import PipelineServices
from src.middleware.error_capture_middleware import capture_run_errors
from src.middleware.run_context_middleware import run_context
from src.presentation.cli.error_translation import readable_failures
from src.presentation.cli.result_output import emit_summary
from src.presentation.schemas.date_range_request_schema import DateRangeRequestSchema


def register(app: typer.Typer, services: PipelineServices) -> None:
    @app.command("transform")
    def transform(
        start_date: str = typer.Option(..., "--start-date"),
        end_date: str = typer.Option(..., "--end-date"),
        source: str = typer.Option("workplace_relations", "--source"),
        body: list[str] = typer.Option(None, "--body"),
    ) -> None:
        # clean what landing already holds and write it into the curated zone
        with readable_failures():
            request = DateRangeRequestSchema(
                start_date=start_date, end_date=end_date, source_name=source, body_codes=tuple(body) if body else None
            )
            with run_context("transform", source, str(request.start_date), str(request.end_date)), capture_run_errors("transform"):
                result = services.transformation.transform_date_range(request.to_transform_dto())
        emit_summary(result)
        raise typer.Exit(code=0 if result.has_no_unexplained_failures else 1)
