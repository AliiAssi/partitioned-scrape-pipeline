from datetime import date, datetime, time, timezone
from typing import Iterator

from pymongo import ASCENDING
from pymongo.database import Database
from pymongo.errors import AutoReconnect, NetworkTimeout, ServerSelectionTimeoutError

from src.application.dto.base.decision_record_dto import DecisionRecordDTO
from src.core.config import Settings
from src.core.logging import get_logger
from src.infrastructure.models.decision_metadata_document import DecisionMetadataDocument
from src.infrastructure.repositories_interfaces.decision_metadata_repository_interface import IDecisionMetadataRepository
from src.utils.retry import call_with_retries

logger = get_logger(__name__)

RETRYABLE_MONGO_ERRORS = (AutoReconnect, NetworkTimeout, ServerSelectionTimeoutError)


class DecisionMetadataRepository(IDecisionMetadataRepository):
    def __init__(self, database: Database, collection_name: str, settings: Settings) -> None:
        self._collection = database[collection_name]
        self._collection_name = collection_name
        self._settings = settings

    def ensure_indexes(self) -> None:
        # the _id is already the composite key, so these are the lookups the services actually run
        self._collection.create_index([("identifier", ASCENDING), ("body_code", ASCENDING)], unique=True)
        self._collection.create_index([("decision_date", ASCENDING), ("body_code", ASCENDING)])
        self._collection.create_index([("partition_date", ASCENDING), ("body_code", ASCENDING)])

    def find_by_identifier_and_body(self, identifier: str, body_code: str) -> DecisionRecordDTO | None:
        # used for the change check that makes a rerun cheap
        document = self._run(lambda: self._collection.find_one({"_id": f"{body_code}:{identifier}"}), "find_by_identifier_and_body")
        return DecisionMetadataDocument.to_dto(document) if document else None

    def upsert(self, record: DecisionRecordDTO) -> None:
        # used for writing metadata; never an insert, so a rerun cannot duplicate
        document = DecisionMetadataDocument.to_document(record)
        self._run(
            lambda: self._collection.replace_one({"_id": document["_id"]}, document, upsert=True),
            "upsert",
        )

    def iterate_by_date_range(self, start_date: date, end_date: date, body_code: str | None = None) -> Iterator[DecisionRecordDTO]:
        # used by the transform stage; the range is half-open to match DatePartition
        query: dict[str, object] = {
            "decision_date": {
                "$gte": datetime.combine(start_date, time.min, tzinfo=timezone.utc),
                "$lt": datetime.combine(end_date, time.min, tzinfo=timezone.utc),
            }
        }
        if body_code:
            query["body_code"] = body_code
        cursor = self._collection.find(query).sort("decision_date", ASCENDING)
        for document in cursor:
            yield DecisionMetadataDocument.to_dto(document)

    def count_by_partition(self, partition_label: str, body_code: str) -> int:
        # used by the coverage checks
        return self._collection.count_documents({"partition_date": partition_label, "body_code": body_code})

    def _run(self, operation, description: str):
        # used for wrapping every call in the same backoff instead of repeating try blocks
        return call_with_retries(
            operation,
            attempts=self._settings.storage_retry_attempts,
            backoff_seconds=self._settings.storage_retry_backoff_seconds,
            retry_on=RETRYABLE_MONGO_ERRORS,
            description=f"mongo.{self._collection_name}.{description}",
        )
