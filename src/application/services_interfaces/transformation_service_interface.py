from abc import ABC, abstractmethod

from src.application.dto.base.date_partition import DatePartition
from src.application.dto.base.partition_result_dto import PartitionResultDTO, RunResultDTO
from src.application.dto.transformation.transform_partition_input_dto import TransformPartitionInputDTO


class ITransformationService(ABC):
    @abstractmethod
    def transform_date_range(self, request: TransformPartitionInputDTO) -> RunResultDTO:
        ...

    @abstractmethod
    def transform_single_partition(self, partition: DatePartition, body_code: str, source_name: str) -> PartitionResultDTO:
        ...
