from dataclasses import dataclass
from datetime import date

from src.application.dto.base.decision_record_dto import DecisionRecordDTO


@dataclass(frozen=True, slots=True)
class IngestPartitionInputDTO:
    source_name: str
    start_date: date
    end_date: date
    body_codes: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class CrawledItemDTO:
    record: DecisionRecordDTO
    payload: bytes | None = None
    error_code: str | None = None
    error_reason: str | None = None

    @property
    def failed(self) -> bool:
        # used so a failed download still counts as a record found, then as a logged failure
        return self.payload is None
