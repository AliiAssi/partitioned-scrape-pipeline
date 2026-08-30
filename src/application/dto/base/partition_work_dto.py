from dataclasses import dataclass
from typing import Any, Iterable

from src.application.dto.base.failure_detail_dto import FailureDetailDTO


@dataclass(frozen=True, slots=True)
class PartitionWorkDTO:
    items: Iterable[Any]
    expected_total: int | None = None
    # listing pages we never managed to read. what the cell contained is then unknown, so no
    # arithmetic over the rows we did parse can prove the cell was fully scraped
    collection_failures: tuple[FailureDetailDTO, ...] = ()
