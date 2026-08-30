import argparse
import logging
from datetime import date

from scrapy.crawler import CrawlerProcess

from src.application.dto.base.date_partition import DatePartition
from src.application.dto.base.source_body import SourceBody
from src.application.services_interfaces.source_service_interface import ISourceService
from src.core.config import get_settings
from src.core.logging import bind_log_context, configure_logging
from src.core.providers import build_source_registry
from src.infrastructure.scraping.scrapy_settings import build_crawler_settings
from src.infrastructure.scraping.spiders.generic_decision_spider import GenericDecisionSpider


def _resolve_body(source_service: ISourceService, body_code: str) -> SourceBody:
    # the subprocess only receives strings, so the body is rebuilt through the source that owns it
    bodies = {body.code: body for body in source_service.list_available_bodies()}
    if body_code not in bodies:
        raise ValueError(f"unknown body code for {source_service.name!r}: {body_code}")
    return bodies[body_code]

# subprocess main
def main() -> None:
    # runs in its own process because twisted's reactor can only be started once per process
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--body-code", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--size", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--run-id", default="")
    arguments = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level)

    partition = DatePartition(
        start=date.fromisoformat(arguments.start),
        end=date.fromisoformat(arguments.end),
        size=arguments.size,
    )
    source_service = build_source_registry().get(arguments.source)
    body = _resolve_body(source_service, arguments.body_code)

    # without this the child's lines carry no run id or partition, and are unattributable once two
    # cells run back to back in the same stream
    bind_log_context(
        run_id=arguments.run_id,
        stage="ingest",
        source=arguments.source,
        partition=partition.label,
        body=body.code,
    )

    crawler_settings = build_crawler_settings(settings)
    crawler_settings["CRAWL_OUTPUT_DIR"] = arguments.output_dir

    process = CrawlerProcess(settings=crawler_settings, install_root_handler=False)
    # CrawlerProcess runs dictConfig(DEFAULT_LOGGING) on construction, which forces the "scrapy" logger
    # to DEBUG and undoes the level configure_logging() just set. install_root_handler=False also means
    # scrapy never installs the handler that LOG_LEVEL would apply to, so it has to be reasserted here,
    # after the reset — otherwise every request and every item is logged through our json formatter.
    logging.getLogger("scrapy").setLevel(crawler_settings["LOG_LEVEL"])
    process.crawl(GenericDecisionSpider, source_service=source_service, body=body, partition=partition)
    process.start()


if __name__ == "__main__":
    main()
