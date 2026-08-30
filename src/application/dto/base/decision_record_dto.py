from dataclasses import dataclass, replace
from datetime import date, datetime, timezone

from src.application.dto.base.content_hash import ContentHash
from src.application.dto.base.object_key import ObjectKey


@dataclass(frozen=True, slots=True)
class DecisionRecordDTO:
    identifier: str
    body_code: str
    body_name: str
    title: str
    description: str
    decision_date: date
    source_url: str
    document_url: str
    partition_date: str
    content_type: str
    source_name: str
    file_path: str | None = None
    file_hash: str | None = None
    content_fingerprint: str | None = None
    scraped_at: datetime | None = None

    @property
    def storage_id(self) -> str:
        # used as the mongo _id, which is what makes a rerun an upsert instead of a duplicate
        return f"{self.body_code}:{self.identifier}"

    @property
    def content_hash(self) -> ContentHash | None:
        # used for comparing what we already stored against what we just fetched
        return ContentHash.from_stored(self.file_hash)

    @property
    def comparison_fingerprint(self) -> ContentHash | None:
        # used for change detection; falls back to the raw hash for records written before fingerprints existed
        return ContentHash.from_stored(self.content_fingerprint) or self.content_hash

    def with_storage(
        self,
        object_key: ObjectKey,
        content_hash: ContentHash,
        content_fingerprint: ContentHash | None = None,
    ) -> "DecisionRecordDTO":
        # used for stamping the storage result onto the record right before it is persisted
        return replace(
            self,
            file_path=str(object_key),
            file_hash=str(content_hash),
            content_fingerprint=str(content_fingerprint or content_hash),
            scraped_at=datetime.now(tz=timezone.utc),
        )
