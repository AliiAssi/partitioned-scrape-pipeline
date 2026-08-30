
from src.application.dto.base.date_partition import DatePartition
from src.application.dto.base.object_key import ObjectKey
from src.application.dto.base.partition_result_dto import PartitionResultDTO, RunResultDTO
from src.application.dto.base.partition_work_dto import PartitionWorkDTO
from src.application.dto.base.source_body import SourceBody
from src.application.dto.base.storage_outcome_dto import StorageOutcomeDTO
from src.application.dto.ingestion.ingest_partition_input_dto import CrawledItemDTO, IngestPartitionInputDTO
from src.application.exceptions import DocumentDownloadError
from src.application.services.base_partition_processing_service import BasePartitionProcessingService
from src.application.services.run_summary_service import RunSummaryService
from src.application.services.sources.source_registry import SourceRegistry
from src.application.services_interfaces.document_storage_service_interface import IDocumentStorageService
from src.application.services_interfaces.ingestion_service_interface import IIngestionService
from src.application.services_interfaces.partition_planning_service_interface import IPartitionPlanningService
from src.core.config import Settings
from src.infrastructure.scraping.crawl_runner_interface import ICrawlRunner


class IngestionService(BasePartitionProcessingService, IIngestionService):
    stage = "ingest"

    def __init__(
        self,
        source_registry: SourceRegistry,
        crawl_runner: ICrawlRunner,
        storage_service: IDocumentStorageService,
        planning_service: IPartitionPlanningService,
        run_summary_service: RunSummaryService,
        settings: Settings,
    ) -> None:
        super().__init__(source_registry, planning_service, run_summary_service)
        self._crawl_runner = crawl_runner
        self._storage_service = storage_service
        self._settings = settings

    def ingest_date_range(self, request: IngestPartitionInputDTO) -> RunResultDTO:
        # used by the cli
        return self.process_date_range(request.source_name, request.start_date, request.end_date, request.body_codes)

    def ingest_single_partition(self, partition: DatePartition, body_code: str, source_name: str) -> PartitionResultDTO:
        # used by dagster, which materialises one cell of the grid at a time
        source_service = self._source_registry.get(source_name)
        body = self._select_bodies(source_service, (body_code,))[0]
        return self.process_partition(partition, body, source_name)

    def collect_items_for_partition(self, partition: DatePartition, body: SourceBody, source_name: str) -> PartitionWorkDTO:
        # used for the crawl itself, which returns one item per record the listing showed
        return self._crawl_runner.crawl_partition(source_name, body, partition)

    def process_single_item(self, item: CrawledItemDTO, partition: DatePartition, body: SourceBody, source_name: str) -> StorageOutcomeDTO:
        # used for storing one raw document exactly as the site served it
        if item.failed:
            raise DocumentDownloadError(
                item.error_reason or "document could not be downloaded",
                identifier=item.record.identifier,
                url=item.record.document_url,
                error_code=item.error_code,
            )
        object_key = ObjectKey.for_landing(
            source_name=source_name,
            body_code=body.code,
            partition_label=partition.label,
            filename=_landing_filename(item.record.document_url, item.record.identifier),
        )
        source_service = self._source_registry.get(source_name)
        return self._storage_service.store_document_if_content_changed(
            item.record,
            item.payload,
            object_key,
            comparison_content=source_service.normalise_for_comparison(item.payload, item.record.content_type),
        )


def _landing_filename(document_url: str, identifier: str) -> str:
    # the raw zone keeps the name the site used; renaming to identifier.ext is the transform stage's job
    tail = document_url.rsplit("/", 1)[-1].split("?")[0]
    return tail if "." in tail else f"{identifier.replace(' ', '')}.html"
