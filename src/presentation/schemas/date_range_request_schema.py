from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from src.application.dto.ingestion.ingest_partition_input_dto import IngestPartitionInputDTO
from src.application.dto.transformation.transform_partition_input_dto import TransformPartitionInputDTO
from src.utils.date_parsing import parse_date


class DateRangeRequestSchema(BaseModel):
    # both stages take the same four inputs, so they are validated once and converted per stage
    model_config = ConfigDict(frozen=True)

    start_date: date
    end_date: date
    source_name: str = "workplace_relations"
    body_codes: tuple[str, ...] | None = None

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def _coerce_date(cls, value: object) -> object:
        # the only place a raw "01/01/2024" from the command line becomes a real date
        return parse_date(value) if isinstance(value, str) else value

    @model_validator(mode="after")
    def _check_range(self) -> "DateRangeRequestSchema":
        # used so an inverted range is rejected at the boundary, not halfway through a run
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self

    def to_ingest_dto(self) -> IngestPartitionInputDTO:
        # used for handing validated input across into the application layer
        return IngestPartitionInputDTO(
            source_name=self.source_name,
            start_date=self.start_date,
            end_date=self.end_date,
            body_codes=self.body_codes,
        )

    def to_transform_dto(self) -> TransformPartitionInputDTO:
        return TransformPartitionInputDTO(
            source_name=self.source_name,
            start_date=self.start_date,
            end_date=self.end_date,
            body_codes=self.body_codes,
        )
