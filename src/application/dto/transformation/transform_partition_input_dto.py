from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class TransformPartitionInputDTO:
    source_name: str
    start_date: date
    end_date: date
    body_codes: tuple[str, ...] | None = None
