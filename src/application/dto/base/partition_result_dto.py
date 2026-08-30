from dataclasses import dataclass, field

from src.application.dto.base.failure_detail_dto import FailureDetailDTO


@dataclass(frozen=True, slots=True)
class PartitionResultDTO:
    partition_label: str
    body_code: str
    stage: str
    records_found: int
    records_written: int
    records_unchanged: int
    duration_seconds: float
    failures: list[FailureDetailDTO] = field(default_factory=list)
    # false when a listing page, or a whole crawl, could not be read for this cell
    collection_complete: bool = True

    @property
    def records_succeeded(self) -> int:
        # used for the "scraped" half of the found-vs-scraped check
        return self.records_written + self.records_unchanged

    @property
    def is_accounted_for(self) -> bool:
        # every record found is either stored or logged as a failure -- and records_found has to
        # mean something, which it does not if we never read the listing that reported it
        if not self.collection_complete:
            return False
        return self.records_found == self.records_succeeded + len(self.failures)

    def as_log_fields(self) -> dict[str, object]:
        # used for the per-partition summary line
        return {
            "stage": self.stage,
            "partition": self.partition_label,
            "body": self.body_code,
            "records_found": self.records_found,
            "records_written": self.records_written,
            "records_unchanged": self.records_unchanged,
            "records_failed": len(self.failures),
            "duration_seconds": round(self.duration_seconds, 3),
            "collection_complete": self.collection_complete,
            "accounted_for": self.is_accounted_for,
        }


@dataclass(frozen=True, slots=True)
class RunResultDTO:
    stage: str
    source_name: str
    start_date: str
    end_date: str
    partitions: list[PartitionResultDTO]

    @property
    def records_found(self) -> int:
        return sum(part.records_found for part in self.partitions)

    @property
    def records_written(self) -> int:
        return sum(part.records_written for part in self.partitions)

    @property
    def records_unchanged(self) -> int:
        return sum(part.records_unchanged for part in self.partitions)

    @property
    def failures(self) -> list[FailureDetailDTO]:
        return [failure for part in self.partitions for failure in part.failures]

    @property
    def collection_complete(self) -> bool:
        # false if any cell's listing could not be read end to end
        return all(part.collection_complete for part in self.partitions)

    @property
    def has_no_unexplained_failures(self) -> bool:
        # used for the cli exit code, so a silently short run cannot look green
        return all(part.is_accounted_for for part in self.partitions)

    def as_log_fields(self) -> dict[str, object]:
        # used for the end-of-run summary line the brief asks for
        return {
            "stage": self.stage,
            "source": self.source_name,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "partitions": len(self.partitions),
            "records_found": self.records_found,
            "records_written": self.records_written,
            "records_unchanged": self.records_unchanged,
            "records_failed": len(self.failures),
            "collection_complete": self.collection_complete,
            "accounted_for": self.has_no_unexplained_failures,
        }
