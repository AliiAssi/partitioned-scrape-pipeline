import json
from datetime import date
from pathlib import Path
from typing import Any

from src.application.dto.base.decision_record_dto import DecisionRecordDTO
from src.core.constants import EXTENSION_BY_CONTENT_TYPE
from src.core.logging import get_logger
from src.utils.text_normalization import slugify_identifier

logger = get_logger(__name__)

ITEMS_FILENAME = "items.jsonl"
DOCUMENTS_DIRNAME = "documents"

# a progress log every N records.
PROGRESS_EVERY_RECORDS = 25


def record_to_row(record: DecisionRecordDTO) -> dict[str, Any]:
    # used for the jsonl handshake between the crawl subprocess and the parent
    return {
        "identifier": record.identifier,
        "body_code": record.body_code,
        "body_name": record.body_name,
        "title": record.title,
        "description": record.description,
        "decision_date": record.decision_date.isoformat(),
        "source_url": record.source_url,
        "document_url": record.document_url,
        "partition_date": record.partition_date,
        "content_type": record.content_type,
        "source_name": record.source_name,
    }


def row_to_record(row: dict[str, Any]) -> DecisionRecordDTO:
    # used for rebuilding the dto on the parent side of that handshake
    return DecisionRecordDTO(
        identifier=row["identifier"],
        body_code=row["body_code"],
        body_name=row["body_name"],
        title=row["title"],
        description=row["description"],
        decision_date=date.fromisoformat(row["decision_date"]),
        source_url=row["source_url"],
        document_url=row["document_url"],
        partition_date=row["partition_date"],
        content_type=row["content_type"],
        source_name=row["source_name"],
    )


def extension_for(content_type: str, url: str) -> str:
    # used for naming the landing file, preferring the served type over the url guess
    normalised = content_type.split(";")[0].strip().lower()
    if normalised in EXTENSION_BY_CONTENT_TYPE:
        return EXTENSION_BY_CONTENT_TYPE[normalised]
    tail = url.rsplit("/", 1)[-1]
    return tail.rsplit(".", 1)[-1].lower() if "." in tail else "html"


class RecordEmittingPipeline:
    def __init__(self, output_dir: str) -> None:
        self._output_root = Path(output_dir)
        self._documents_dir = self._output_root / DOCUMENTS_DIRNAME
        self._items_file = None
        self._handled = 0
        self._reported_total: int | None = None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(output_dir=crawler.settings.get("CRAWL_OUTPUT_DIR"))

    def open_spider(self, spider=None) -> None:
        # used for preparing the handoff directory before the first item arrives
        self._documents_dir.mkdir(parents=True, exist_ok=True)
        self._items_file = (self._output_root / ITEMS_FILENAME).open("w", encoding="utf-8")

    def close_spider(self, spider=None) -> None:
        # used so the parent process never reads a half-written line
        if self._items_file is not None:
            self._items_file.flush()
            self._items_file.close()
            self._items_file = None
        logger.info("crawl_finished", extra={"handled": self._handled, "reported_total": self._reported_total})
        
    # Scrapy calls process_item for every dict the spider yields.
    def process_item(self, item, spider=None):
        # used for writing one line per record found, whether its document arrived or not
        if item.get("listing_failed"):
            row = {
                "row_type": "listing_failure",
                "url": item.get("url"),
                "page_number": item.get("page_number"),
                "error_code": item.get("error_code"),
                "error_reason": item.get("error_reason"),
            }
            self._items_file.write(json.dumps(row, ensure_ascii=False) + "\n")
            logger.error("listing_page_unreadable", extra={k: v for k, v in row.items() if k != "row_type"})
            return item

        if "reported_total" in item:
            self._reported_total = item["reported_total"]
            self._items_file.write(json.dumps({"row_type": "summary", "reported_total": item["reported_total"]}) + "\n")
            return item

        record: DecisionRecordDTO = item["record"]
        row = record_to_row(record)
        row["row_type"] = "record"
        payload: bytes | None = item.get("payload")

        if payload is None:
            row.update({"local_path": None, "error_code": item.get("error_code"), "error_reason": item.get("error_reason")})
        else:
            content_type = item.get("content_type") or record.content_type
            extension = extension_for(content_type, record.document_url)
            # the counter is what keeps two rows apart when they share a case reference: the site
            # does reuse them, and without it both rows read back whichever document landed last
            filename = f"{slugify_identifier(record.identifier)}-{self._handled}.{extension}"
            (self._documents_dir / filename).write_bytes(payload)
            row.update({"local_path": str(self._documents_dir / filename), "content_type": content_type, "error_code": None, "error_reason": None})

        self._items_file.write(json.dumps(row, ensure_ascii=False) + "\n")
        self._handled += 1
        if self._handled % PROGRESS_EVERY_RECORDS == 0:
            logger.info("crawl_progress", extra={"handled": self._handled, "reported_total": self._reported_total})
        return item
