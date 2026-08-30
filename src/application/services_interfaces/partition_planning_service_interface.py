from abc import ABC, abstractmethod
from datetime import date

from src.application.dto.base.date_partition import DatePartition


class IPartitionPlanningService(ABC):
    @abstractmethod
    def plan_partitions(self, start_date: date, end_date: date, partition_size: str | None = None) -> list[DatePartition]:
        # used for splitting a date range into the units of work everything else retries on
        ...

    @abstractmethod
    def partition_starting_at(self, start_date: date, partition_size: str | None = None) -> DatePartition:
        # used by dagster, whose grid hands back one period start rather than a range
        ...
