import typer

from src.core.providers import PipelineServices
from src.middleware.error_capture_middleware import capture_run_errors
from src.middleware.run_context_middleware import run_context
from src.presentation.cli.error_translation import readable_failures
from src.presentation.cli.result_output import emit_summary
from src.presentation.schemas.date_range_request_schema import DateRangeRequestSchema


def register(app: typer.Typer, services: PipelineServices) -> None:
    @app.command("ingest")
    def ingest(
        start_date: str = typer.Option(..., "--start-date", help="inclusive, dd/mm/yyyy or yyyy-mm-dd"),
        end_date: str = typer.Option(..., "--end-date", help="exclusive, dd/mm/yyyy or yyyy-mm-dd"),
        source: str = typer.Option("workplace_relations", "--source"),
        body: list[str] = typer.Option(None, "--body", help="repeatable; defaults to every body"),
    ) -> None:
        # scrape a date range into the landing zone
        with readable_failures():
            request = DateRangeRequestSchema(
                start_date=start_date, end_date=end_date, source_name=source, body_codes=tuple(body) if body else None
            )
            with run_context("ingest", source, str(request.start_date), str(request.end_date)), capture_run_errors("ingest"):
                result = services.ingestion.ingest_date_range(request.to_ingest_dto())
        emit_summary(result)
        raise typer.Exit(code=0 if result.has_no_unexplained_failures else 1)
