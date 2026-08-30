import re

from src.application.dto.base.date_partition import DatePartition
from src.application.dto.base.decision_record_dto import DecisionRecordDTO
from src.application.dto.base.object_key import ObjectKey
from src.application.dto.base.partition_result_dto import PartitionResultDTO, RunResultDTO
from src.application.dto.base.partition_work_dto import PartitionWorkDTO
from src.application.dto.base.source_body import SourceBody
from src.application.dto.base.storage_outcome_dto import StorageOutcomeDTO
from src.application.dto.transformation.transform_partition_input_dto import TransformPartitionInputDTO
from src.application.exceptions import ContentExtractionError, DocumentReadError
from src.application.services.base_partition_processing_service import BasePartitionProcessingService
from src.application.services.run_summary_service import RunSummaryService
from src.application.services.sources.source_registry import SourceRegistry
from src.application.services_interfaces.document_storage_service_interface import IDocumentStorageService
from src.application.services_interfaces.partition_planning_service_interface import IPartitionPlanningService
from src.application.services_interfaces.transformation_service_interface import ITransformationService
from src.core.config import Settings
from src.infrastructure.object_storage_interfaces.object_store_interface import IReadOnlyObjectStore
from src.infrastructure.repositories_interfaces.decision_metadata_repository_interface import IDecisionMetadataRepository


class TransformationService(BasePartitionProcessingService, ITransformationService):
    stage = "transform"

    def __init__(
        self,
        source_registry: SourceRegistry,
        landing_repository: IDecisionMetadataRepository,
        landing_object_store: IReadOnlyObjectStore,
        storage_service: IDocumentStorageService,
        planning_service: IPartitionPlanningService,
        run_summary_service: RunSummaryService,
        settings: Settings,
    ) -> None:
        # the landing store arrives typed read-only, so this service has no way to touch the raw zone
        super().__init__(source_registry, planning_service, run_summary_service)
        self._landing_repository = landing_repository
        self._landing_object_store = landing_object_store
        self._storage_service = storage_service
        self._settings = settings

    def transform_date_range(self, request: TransformPartitionInputDTO) -> RunResultDTO:
        # used by the cli
        return self.process_date_range(request.source_name, request.start_date, request.end_date, request.body_codes)

    def transform_single_partition(self, partition: DatePartition, body_code: str, source_name: str) -> PartitionResultDTO:
        # used by dagster, one cell at a time, downstream of the same cell's ingest
        source_service = self._source_registry.get(source_name)
        body = self._select_bodies(source_service, (body_code,))[0]
        return self.process_partition(partition, body, source_name)

    def collect_items_for_partition(self, partition: DatePartition, body: SourceBody, source_name: str) -> PartitionWorkDTO:
        # used for reading what landing already holds for this cell, rather than going back to the site
        records = [
            record
            for record in self._landing_repository.iterate_by_date_range(partition.start, partition.end, body.code)
            if record.file_path
        ]
        return PartitionWorkDTO(items=records, expected_total=len(records))

    def process_single_item(self, item: DecisionRecordDTO, partition: DatePartition, body: SourceBody, source_name: str) -> StorageOutcomeDTO:
        # used for cleaning one document, renaming it, and writing it into the curated zone
        source_service = self._source_registry.get(source_name)
        try:
            raw = self._landing_object_store.get_object(ObjectKey(item.file_path))
        except Exception as error:
            raise DocumentReadError(
                str(error), identifier=item.identifier, url=item.file_path, error_code="landing_object_unreadable"
            ) from error

        try:
            content = source_service.extract_relevant_content(raw, item.content_type)
        except ContentExtractionError as error:
            raise ContentExtractionError(
                str(error), identifier=item.identifier, url=item.source_url, error_code="content_extraction_failed"
            ) from error

        object_key = ObjectKey.for_curated(
            source_name=source_name,
            body_code=body.code,
            partition_label=partition.label,
            identifier=_curated_identifier(item.identifier),
            extension=_extension_of(item.file_path),
        )
        return self._storage_service.store_document_if_content_changed(item, content, object_key)


def _curated_identifier(identifier: str) -> str:
    # the brief asks for identifier.ext; "IR - SC - 00001785" becomes IR-SC-00001785 so the key stays clean
    return re.sub(r"\s+", "", identifier)


def _extension_of(file_path: str) -> str:
    # used for keeping the original format, since pdfs and docs pass through untouched
    tail = file_path.rsplit("/", 1)[-1]
    return tail.rsplit(".", 1)[-1].lower() if "." in tail else "html"
