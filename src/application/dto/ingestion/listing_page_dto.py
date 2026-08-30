from dataclasses import dataclass, field

from src.application.dto.base.decision_record_dto import DecisionRecordDTO


@dataclass(frozen=True, slots=True)
class ListingPageDTO:
    records: list[DecisionRecordDTO] = field(default_factory=list)
    reported_total: int | None = None

    @property
    def is_empty(self) -> bool:
        # used as the pagination stop condition, instead of trusting a scraped total
        return not self.records
