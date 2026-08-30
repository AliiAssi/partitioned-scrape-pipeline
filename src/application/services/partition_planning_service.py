from datetime import date, timedelta

from src.application.dto.base.date_partition import DatePartition
from src.application.services_interfaces.partition_planning_service_interface import IPartitionPlanningService
from src.core.config import Settings


def _first_day_of_next_month(value: date) -> date:
    # used for stepping a monthly window without any day-of-month arithmetic
    return date(value.year + 1, 1, 1) if value.month == 12 else date(value.year, value.month + 1, 1)


class PartitionPlanningService(IPartitionPlanningService):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def plan_partitions(self, start_date: date, end_date: date, partition_size: str | None = None) -> list[DatePartition]:
        # the one place a date range becomes units of work, so the cli and dagster cannot disagree
        size = partition_size or self._settings.partition_size
        if end_date <= start_date:
            raise ValueError(f"end_date {end_date} must be after start_date {start_date}")

        partitions: list[DatePartition] = []
        cursor = start_date
        while cursor < end_date:
            boundary = min(self._next_boundary(cursor, size), end_date)
            partitions.append(DatePartition(start=cursor, end=boundary, size=size))
            cursor = boundary
        return partitions

    def partition_starting_at(self, start_date: date, partition_size: str | None = None) -> DatePartition:
        # dagster addresses one cell at a time, so it needs the period that begins on this date. the
        # size defaults to the configured one, which is also what the grid was built from.
        size = partition_size or self._settings.partition_size
        return DatePartition(start=start_date, end=self._next_boundary(start_date, size), size=size)

    def _next_boundary(self, cursor: date, size: str) -> date:
        # used for the step itself; every size lands on a boundary the next window starts from
        if size == "monthly":
            return _first_day_of_next_month(cursor)
        if size == "weekly":
            return cursor + timedelta(days=7)
        return cursor + timedelta(days=1)
