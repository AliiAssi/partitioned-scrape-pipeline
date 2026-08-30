import time

from src.application.dto.base.date_partition import DatePartition
from src.application.dto.base.failure_detail_dto import FailureDetailDTO
from src.application.dto.base.partition_result_dto import PartitionResultDTO
from src.application.dto.base.source_body import SourceBody
from src.application.dto.base.storage_outcome_dto import StorageOutcomeDTO
from src.core.logging import get_logger

logger = get_logger(__name__)


class PartitionSummary:
    def __init__(self, stage: str, partition: DatePartition, body: SourceBody) -> None:
        self._stage = stage
        self._partition = partition
        self._body = body
        self._started_at = time.monotonic()
        self._expected_total: int | None = None
        self._collection_complete = True
        self._collected = 0
        self._written = 0
        self._unchanged = 0
        self._failures: list[FailureDetailDTO] = []

    def set_expected_total(self, expected_total: int | None) -> None:
        # the site prints its own result count, which is the only found number we did not derive ourselves
        self._expected_total = expected_total

    def record_outcome(self, outcome: StorageOutcomeDTO) -> None:
        # used for one successfully handled record
        self._collected += 1
        if outcome.was_written:
            self._written += 1
        else:
            self._unchanged += 1

    def record_collection_failure(self, failure: FailureDetailDTO) -> None:
        # a listing page, or a whole crawl, we never read. it is counted as a failure so it appears
        # in the log with its url and reason, and it also marks the cell's inventory incomplete so
        # the partition cannot reconcile however neatly its own arithmetic happens to add up
        self._collection_complete = False
        self._failures.append(failure)
        logger.error(
            "partition_collection_incomplete",
            extra={"stage": self._stage, "partition": self._partition.label, "body": self._body.code, **failure.as_log_fields()},
        )

    def record_failure(self, failure: FailureDetailDTO) -> None:
        # used so every record we could not store is named in the log with its reason
        self._collected += 1
        self._failures.append(failure)
        logger.error(
            "record_failed",
            extra={"stage": self._stage, "partition": self._partition.label, "body": self._body.code, **failure.as_log_fields()},
        )

    def finalize(self) -> PartitionResultDTO:
        # used for closing the partition and emitting its one summary line
        records_found = self._expected_total if self._expected_total is not None else self._collected
        result = PartitionResultDTO(
            partition_label=self._partition.label,
            body_code=self._body.code,
            stage=self._stage,
            records_found=records_found,
            records_written=self._written,
            records_unchanged=self._unchanged,
            duration_seconds=time.monotonic() - self._started_at,
            failures=list(self._failures),
            collection_complete=self._collection_complete,
        )
        if not result.is_accounted_for:
            logger.error(
                "partition_unaccounted_records",
                extra={
                    "stage": self._stage,
                    "partition": self._partition.label,
                    "body": self._body.code,
                    "reported_by_site": records_found,
                    "handled": result.records_succeeded + len(self._failures),
                    "collection_complete": self._collection_complete,
                },
            )
        logger.info("partition_completed", extra=result.as_log_fields())
        return result


class RunSummaryService:
    def begin_partition(self, stage: str, partition: DatePartition, body: SourceBody) -> PartitionSummary:
        # used for opening the counters that every stage reports through
        logger.info("partition_started", extra={"stage": stage, "partition": partition.label, "body": body.code})
        return PartitionSummary(stage=stage, partition=partition, body=body)
