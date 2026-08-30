import typer

from src.core.providers import PipelineServices
from src.middleware.error_capture_middleware import capture_run_errors
from src.middleware.run_context_middleware import run_context
from src.presentation.cli.error_translation import readable_failures
from src.presentation.cli.result_output import emit_summary
from src.presentation.schemas.date_range_request_schema import DateRangeRequestSchema


def register(app: typer.Typer, services: PipelineServices) -> None:
    @app.command("run")
    def run(
        start_date: str = typer.Option(..., "--start-date"),
        end_date: str = typer.Option(..., "--end-date"),
        source: str = typer.Option("workplace_relations", "--source"),
        body: list[str] = typer.Option(None, "--body"),
    ) -> None:
        # both stages in order, for when you do not want to start the orchestrator
        with readable_failures():
            request = DateRangeRequestSchema(
                start_date=start_date, end_date=end_date, source_name=source, body_codes=tuple(body) if body else None
            )
            with run_context("full", source, str(request.start_date), str(request.end_date)), capture_run_errors("full"):
                ingest_result = services.ingestion.ingest_date_range(request.to_ingest_dto())
                transform_result = services.transformation.transform_date_range(request.to_transform_dto())

        emit_summary(ingest_result)
        emit_summary(transform_result)
        succeeded = ingest_result.has_no_unexplained_failures and transform_result.has_no_unexplained_failures
        raise typer.Exit(code=0 if succeeded else 1)
