from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True, slots=True)
class DatePartition:
    start: date
    end: date
    size: str

    def __post_init__(self) -> None:
        # used for making an inverted or empty window impossible to construct
        if self.end <= self.start:
            raise ValueError(f"partition end {self.end} must be after start {self.start}")
        if self.size not in {"daily", "weekly", "monthly"}:
            raise ValueError(f"unsupported partition size: {self.size}")

    @property
    def label(self) -> str:
        # used as the canonical partition_date written on every record
        if self.size == "monthly":
            return self.start.strftime("%Y-%m")
        if self.size == "weekly":
            return f"{self.start.isocalendar().year}-W{self.start.isocalendar().week:02d}"
        return self.start.isoformat()

    @property
    def last_included_day(self) -> date:
        # used for the site filter, which treats the finish date as inclusive
        return self.end - timedelta(days=1)

    def contains(self, value: date) -> bool:
        # used for checking a scraped date really belongs to the partition we asked for
        return self.start <= value < self.end
