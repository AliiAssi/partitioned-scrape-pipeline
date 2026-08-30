from datetime import date, datetime, time, timezone
from typing import Any

from src.application.dto.base.decision_record_dto import DecisionRecordDTO


def _to_datetime(value: date) -> datetime:
    # used because bson stores datetimes, not dates
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def _to_date(value: Any) -> date:
    # used for reading that datetime back as the date it always was
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raise TypeError(f"cannot read a date out of {value!r}")


class DecisionMetadataDocument:
    @staticmethod
    def to_document(record: DecisionRecordDTO) -> dict[str, Any]:
        # used for the shape that actually lands in the collection
        return {
            "_id": record.storage_id,
            "identifier": record.identifier,
            "body_code": record.body_code,
            "body_name": record.body_name,
            "title": record.title,
            "description": record.description,
            "decision_date": _to_datetime(record.decision_date),
            "source_url": record.source_url,
            "document_url": record.document_url,
            "partition_date": record.partition_date,
            "content_type": record.content_type,
            "source_name": record.source_name,
            "file_path": record.file_path,
            "file_hash": record.file_hash,
            "content_fingerprint": record.content_fingerprint,
            "scraped_at": record.scraped_at,
        }

    @staticmethod
    def to_dto(document: dict[str, Any]) -> DecisionRecordDTO:
        # used for turning a stored document back into the dto the services work with
        return DecisionRecordDTO(
            identifier=document["identifier"],
            body_code=document["body_code"],
            body_name=document["body_name"],
            title=document["title"],
            description=document.get("description", ""),
            decision_date=_to_date(document["decision_date"]),
            source_url=document["source_url"],
            document_url=document["document_url"],
            partition_date=document["partition_date"],
            content_type=document["content_type"],
            source_name=document["source_name"],
            file_path=document.get("file_path"),
            file_hash=document.get("file_hash"),
            content_fingerprint=document.get("content_fingerprint"),
            scraped_at=document.get("scraped_at"),
        )
