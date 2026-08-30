from abc import ABC, abstractmethod

from src.application.dto.base.date_partition import DatePartition
from src.application.dto.base.partition_result_dto import PartitionResultDTO, RunResultDTO
from src.application.dto.ingestion.ingest_partition_input_dto import IngestPartitionInputDTO


class IIngestionService(ABC):
    @abstractmethod
    def ingest_date_range(self, request: IngestPartitionInputDTO) -> RunResultDTO:
        # used by the cli, which hands over a whole range at once
        ...

    @abstractmethod
    def ingest_single_partition(self, partition: DatePartition, body_code: str, source_name: str) -> PartitionResultDTO:
        # used by dagster, which materialises one cell of the grid at a time
        ...
