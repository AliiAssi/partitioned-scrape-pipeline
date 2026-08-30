from abc import ABC, abstractmethod
from datetime import date
from typing import Any

from src.application.dto.base.date_partition import DatePartition
from src.application.dto.base.failure_detail_dto import FailureDetailDTO
from src.application.dto.base.partition_result_dto import PartitionResultDTO, RunResultDTO
from src.application.dto.base.partition_work_dto import PartitionWorkDTO
from src.application.dto.base.source_body import SourceBody
from src.application.dto.base.storage_outcome_dto import StorageOutcomeDTO
from src.application.exceptions import PartitionIngestionError, RecordProcessingError
from src.application.services.sources.source_registry import SourceRegistry
from src.application.services.run_summary_service import RunSummaryService
from src.application.services_interfaces.partition_planning_service_interface import IPartitionPlanningService
from src.application.services_interfaces.source_service_interface import ISourceService
from src.core.logging import get_logger

logger = get_logger(__name__)


class BasePartitionProcessingService(ABC):
    stage: str = "unknown"

    def __init__(
        self,
        source_registry: SourceRegistry,
        planning_service: IPartitionPlanningService,
        run_summary_service: RunSummaryService,
    ) -> None:
        self._source_registry = source_registry
        self._planning_service = planning_service
        self._run_summary_service = run_summary_service

    def process_date_range(
        self,
        source_name: str,
        start_date: date,
        end_date: date,
        body_codes: tuple[str, ...] | None = None,
    ) -> RunResultDTO:
        # used by the cli, which asks for a whole range and gets back one summary for the run
        source_service = self._source_registry.get(source_name)
        bodies = self._select_bodies(source_service, body_codes)
        partitions = self._planning_service.plan_partitions(start_date, end_date)

        results = [
            self.process_partition(partition, body, source_name)
            for partition in partitions
            for body in bodies
        ]
        run_result = RunResultDTO(
            stage=self.stage,
            source_name=source_name,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            partitions=results,
        )
        logger.info("run_completed", extra=run_result.as_log_fields())
        return run_result

    def process_partition(self, partition: DatePartition, body: SourceBody, source_name: str) -> PartitionResultDTO:
        # the loop, the failure handling and the counting live here once, for both stages
        summary = self._run_summary_service.begin_partition(self.stage, partition, body)
        try:
            work = self.collect_items_for_partition(partition, body, source_name)
        except PartitionIngestionError as error:
            # this cell could not be collected at all. it is recorded and the run carries on with
            # the remaining cells, rather than throwing their work away over one failed crawl
            summary.record_collection_failure(FailureDetailDTO.from_error(error))
            return summary.finalize()

        summary.set_expected_total(work.expected_total)
        for failure in work.collection_failures:
            summary.record_collection_failure(failure)
        for item in work.items:
            try:
                summary.record_outcome(self.process_single_item(item, partition, body, source_name))
            except RecordProcessingError as error:
                summary.record_failure(FailureDetailDTO.from_error(error))
        return summary.finalize()

    def _select_bodies(self, source_service: ISourceService, body_codes: tuple[str, ...] | None) -> list[SourceBody]:
        # used for the --bodies flag; an unknown code fails here rather than silently scraping nothing
        available = source_service.list_available_bodies()
        if not body_codes:
            return available
        by_code = {body.code: body for body in available}
        unknown = [code for code in body_codes if code not in by_code]
        if unknown:
            raise ValueError(f"unknown body codes: {', '.join(unknown)}")
        return [by_code[code] for code in body_codes]

    @abstractmethod
    def collect_items_for_partition(self, partition: DatePartition, body: SourceBody, source_name: str) -> PartitionWorkDTO:
        # the one step that actually differs between ingest and transform
        ...

    @abstractmethod
    def process_single_item(self, item: Any, partition: DatePartition, body: SourceBody, source_name: str) -> StorageOutcomeDTO:
        # the other step that differs; everything around it is shared
        ...
