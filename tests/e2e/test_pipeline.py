from datetime import date

import pytest

from src.application.dto.base.failure_detail_dto import FailureDetailDTO
from src.application.dto.base.partition_work_dto import PartitionWorkDTO
from src.application.dto.ingestion.ingest_partition_input_dto import CrawledItemDTO, IngestPartitionInputDTO
from src.application.dto.transformation.transform_partition_input_dto import TransformPartitionInputDTO
from src.application.services.document_storage_service import DocumentStorageService
from src.application.services.ingestion_service import IngestionService
from src.application.services.partition_planning_service import PartitionPlanningService
from src.application.services.run_summary_service import RunSummaryService
from src.application.services.sources.source_registry import SourceRegistry
from src.application.services.sources.workplace_relations.wrc_content_extractor import WrcContentExtractor
from src.application.services.sources.workplace_relations.wrc_listing_parser import WrcListingParser
from src.application.services.sources.workplace_relations.wrc_source_service import WrcSourceService
from src.application.services.transformation_service import TransformationService
from src.application.exceptions import PartitionIngestionError
from src.core.config import Settings
from src.infrastructure.scraping.crawl_runner_interface import ICrawlRunner
from tests.fakes import FakeMetadataRepository, FakeObjectStore
from tests.fixtures import DECISION_PAGE, DECISION_PAGE_RESERVED, LISTING_PAGE

INGEST = IngestPartitionInputDTO("workplace_relations", date(2024, 1, 1), date(2024, 2, 1))
TRANSFORM = TransformPartitionInputDTO("workplace_relations", date(2024, 1, 1), date(2024, 2, 1))


class FixtureCrawlRunner(ICrawlRunner):
    def __init__(self, source_service: WrcSourceService) -> None:
        # stands in for scrapy so the pipeline can run end to end without the network
        self._source_service = source_service
        self.decision_page = DECISION_PAGE
        self.crawl_calls = 0
        # the two ways a real crawl fails: the subprocess dies, or a listing page never arrives
        self.crash_bodies: set[str] = set()
        self.unreadable_listing_bodies: set[str] = set()

    def crawl_partition(self, source_name, body, partition) -> PartitionWorkDTO:
        self.crawl_calls += 1
        if body.code in self.crash_bodies:
            raise PartitionIngestionError(f"crawl failed for {body.code} {partition.label}")
        if body.code in self.unreadable_listing_bodies:
            return PartitionWorkDTO(
                items=[],
                expected_total=None,
                collection_failures=(
                    FailureDetailDTO(
                        identifier=None,
                        url="https://example.test/en/search/?pageNumber=1",
                        error_code="504",
                        reason="504 Gateway Timeout",
                    ),
                ),
            )
        if body.code != "wrc":
            return PartitionWorkDTO(items=[], expected_total=0)
        page = self._source_service.parse_listing_page(LISTING_PAGE, body, partition)
        items = [CrawledItemDTO(record=record, payload=self.decision_page) for record in page.records]
        return PartitionWorkDTO(items=items, expected_total=len(items))


@pytest.fixture
def pipeline():
    settings = Settings()
    source_service = WrcSourceService(WrcListingParser(), WrcContentExtractor())
    registry = SourceRegistry([source_service])
    planner = PartitionPlanningService(settings)
    summaries = RunSummaryService()
    runner = FixtureCrawlRunner(source_service)

    landing_repository, landing_store = FakeMetadataRepository(), FakeObjectStore()
    curated_repository, curated_store = FakeMetadataRepository(), FakeObjectStore()

    ingestion = IngestionService(
        source_registry=registry,
        crawl_runner=runner,
        storage_service=DocumentStorageService(landing_repository, landing_store),
        planning_service=planner,
        run_summary_service=summaries,
        settings=settings,
    )
    transformation = TransformationService(
        source_registry=registry,
        landing_repository=landing_repository,
        landing_object_store=landing_store,
        storage_service=DocumentStorageService(curated_repository, curated_store),
        planning_service=planner,
        run_summary_service=summaries,
        settings=settings,
    )
    return ingestion, transformation, runner, landing_store, curated_store


def test_a_first_run_stores_every_record_it_found(pipeline):
    ingestion, _, runner, landing_store, _ = pipeline

    result = ingestion.ingest_date_range(INGEST)

    assert result.records_written == 3
    assert len(result.failures) == 0
    assert result.has_no_unexplained_failures
    assert len(landing_store.objects) == 3
    # no body carries active-date bounds any more, so every one of the four is asked
    assert runner.crawl_calls == 4


def test_a_second_run_writes_nothing_even_when_the_render_time_moved(pipeline):
    ingestion, _, runner, landing_store, _ = pipeline

    ingestion.ingest_date_range(INGEST)
    runner.decision_page = DECISION_PAGE_RESERVED
    second = ingestion.ingest_date_range(INGEST)

    assert second.records_written == 0
    assert second.records_unchanged == 3
    assert landing_store.put_calls == 3


def test_one_dead_crawl_fails_its_own_cell_without_discarding_the_rest_of_the_run(pipeline):
    ingestion, _, runner, landing_store, _ = pipeline
    runner.crash_bodies = {"labour_court"}

    result = ingestion.ingest_date_range(INGEST)

    assert runner.crawl_calls == 4, "the cells after the failed one must still be attempted"
    assert result.records_written == 3, "wrc still stored everything it found"
    assert len(landing_store.objects) == 3
    assert [failure.error_code for failure in result.failures] == ["PartitionIngestionError"]
    assert not result.has_no_unexplained_failures, "the run still has to exit non-zero"


def test_an_unread_listing_page_stops_an_empty_cell_from_looking_green(pipeline):
    ingestion, _, runner, _, _ = pipeline
    runner.unreadable_listing_bodies = {"wrc"}

    result = ingestion.ingest_date_range(INGEST)
    wrc = next(part for part in result.partitions if part.body_code == "wrc")

    # nothing was found and no record failed, so before this the arithmetic held and the cell
    # reported accounted_for true having stored nothing at all
    assert wrc.records_found == 0 and wrc.records_written == 0
    assert not wrc.collection_complete
    assert not wrc.is_accounted_for
    assert not result.has_no_unexplained_failures


def test_transform_cleans_renames_and_leaves_the_landing_zone_alone(pipeline):
    ingestion, transformation, _, landing_store, curated_store = pipeline

    ingestion.ingest_date_range(INGEST)
    landing_before = dict(landing_store.objects)
    result = transformation.transform_date_range(TRANSFORM)

    assert result.records_written == 3
    assert landing_store.objects == landing_before
    assert sorted(key.rsplit("/", 1)[-1] for key in curated_store.objects) == [
        "ADJ-00035852.html",
        "ADJ-00047352.html",
        "IR-SC-00001785.html",
    ]
    cleaned = next(iter(curated_store.objects.values()))
    assert b"Summary of Workers Case" in cleaned and b"Return to Search" not in cleaned
