from abc import ABC, abstractmethod

from src.application.dto.base.date_partition import DatePartition
from src.application.dto.base.partition_work_dto import PartitionWorkDTO
from src.application.dto.base.source_body import SourceBody


class ICrawlRunner(ABC):
    @abstractmethod
    def crawl_partition(self, source_name: str, body: SourceBody, partition: DatePartition) -> PartitionWorkDTO:
        # used for one (month, body) cell; one item per record found, plus the total the site reported
        ...
