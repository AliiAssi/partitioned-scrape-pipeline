from datetime import date
from typing import Iterator

from src.application.dto.base.decision_record_dto import DecisionRecordDTO
from src.application.dto.base.object_key import ObjectKey
from src.infrastructure.object_storage_interfaces.object_store_interface import IObjectStore
from src.infrastructure.repositories_interfaces.decision_metadata_repository_interface import IDecisionMetadataRepository


class FakeMetadataRepository(IDecisionMetadataRepository):
    def __init__(self) -> None:
        self.documents: dict[str, DecisionRecordDTO] = {}

    def ensure_indexes(self) -> None:
        pass

    def find_by_identifier_and_body(self, identifier: str, body_code: str) -> DecisionRecordDTO | None:
        return self.documents.get(f"{body_code}:{identifier}")

    def upsert(self, record: DecisionRecordDTO) -> None:
        self.documents[record.storage_id] = record

    def iterate_by_date_range(self, start_date: date, end_date: date, body_code: str | None = None) -> Iterator[DecisionRecordDTO]:
        for record in self.documents.values():
            if start_date <= record.decision_date < end_date and (body_code is None or record.body_code == body_code):
                yield record

    def count_by_partition(self, partition_label: str, body_code: str) -> int:
        return sum(1 for r in self.documents.values() if r.partition_date == partition_label and r.body_code == body_code)


class FakeObjectStore(IObjectStore):
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.put_calls = 0

    def ensure_bucket(self) -> None:
        pass

    def put_object(self, key: ObjectKey, payload: bytes, content_type: str) -> None:
        self.put_calls += 1
        self.objects[key.value] = payload

    def get_object(self, key: ObjectKey) -> bytes:
        return self.objects[key.value]

    def object_exists(self, key: ObjectKey) -> bool:
        return key.value in self.objects
