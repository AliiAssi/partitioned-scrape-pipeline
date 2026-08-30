import typer

from src.core.config import get_settings
from src.core.logging import configure_logging, get_logger
from src.core.providers import PipelineServices, build_services
from src.presentation.cli import ingest_command, run_full_pipeline_command, transform_command

logger = get_logger(__name__)


def build_application() -> tuple[typer.Typer, PipelineServices]:
    # the composition root: config, logging, dependency graph, then the commands on top
    settings = get_settings()
    configure_logging(settings.log_level)
    services = build_services(settings)

    app = typer.Typer(add_completion=False, help="Workplace Relations decisions pipeline")

    @app.callback()
    def bootstrap() -> None:
        # runs before every command, so buckets and indexes exist before the first partition
        if not services.mongo.check_health():
            raise typer.Exit(code=2)
        services.prepare_storage()

    ingest_command.register(app, services)
    transform_command.register(app, services)
    run_full_pipeline_command.register(app, services)
    return app, services


def main() -> None:
    # used as the console entrypoint; connections are closed on the way out
    app, services = build_application()
    try:
        app()
    finally:
        services.close()


if __name__ == "__main__":
    main()
