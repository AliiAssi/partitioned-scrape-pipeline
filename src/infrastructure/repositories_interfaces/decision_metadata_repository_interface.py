from abc import ABC, abstractmethod
from datetime import date
from typing import Iterator

from src.application.dto.base.decision_record_dto import DecisionRecordDTO


class IDecisionMetadataRepository(ABC):
    @abstractmethod
    def ensure_indexes(self) -> None:
        # used for the unique key that stops duplicates even if the code is wrong
        ...

    @abstractmethod
    def find_by_identifier_and_body(self, identifier: str, body_code: str) -> DecisionRecordDTO | None:
        # used for the change check before a write
        ...

    @abstractmethod
    def upsert(self, record: DecisionRecordDTO) -> None:
        # used for writing metadata without ever creating a second copy of a record
        ...

    @abstractmethod
    def iterate_by_date_range(self, start_date: date, end_date: date, body_code: str | None = None) -> Iterator[DecisionRecordDTO]:
        # used by the transform stage to find what landing already holds
        ...

    @abstractmethod
    def count_by_partition(self, partition_label: str, body_code: str) -> int:
        # used for the coverage checks in tests and analysis
        ...
