from bs4 import BeautifulSoup

from src.application.dto.base.date_partition import DatePartition
from src.application.dto.base.decision_record_dto import DecisionRecordDTO
from src.application.dto.base.source_body import SourceBody
from src.application.dto.ingestion.listing_page_dto import ListingPageDTO
from src.application.services.sources.workplace_relations import wrc_config
from src.core.constants import EXTENSION_BY_CONTENT_TYPE
from src.core.logging import get_logger
from src.utils.date_parsing import parse_date
from src.utils.text_normalization import collapse_whitespace

logger = get_logger(__name__)

# first content type wins, so ".html" resolves to text/html rather than the xhtml alias
_CONTENT_TYPE_BY_EXTENSION: dict[str, str] = {}
for _content_type, _extension in EXTENSION_BY_CONTENT_TYPE.items():
    _CONTENT_TYPE_BY_EXTENSION.setdefault(_extension, _content_type)


class WrcListingParser:
    def parse(self, payload: bytes, body: SourceBody, partition: DatePartition, source_name: str) -> ListingPageDTO:
        # used for reading the ten result rows off one search page
        soup = BeautifulSoup(payload, "html.parser")
        records = []
        for item in soup.select(wrc_config.LISTING_ROW_SELECTOR):
            record = self._parse_item(item, body, partition, source_name)
            if record is not None:
                records.append(record)
        return ListingPageDTO(records=records, reported_total=self._read_reported_total(soup))

    def _read_reported_total(self, soup) -> int | None:
        # the site prints "234 results", which gives us a count independent of the rows we parsed
        match = wrc_config.REPORTED_TOTAL_PATTERN.search(soup.get_text(" "))
        return int(match.group(1).replace(",", "")) if match else None

    def _parse_item(self, item, body: SourceBody, partition: DatePartition, source_name: str) -> DecisionRecordDTO | None:
        # used for one result row; a row missing its link or date is skipped and logged rather than guessed at
        link = item.select_one(wrc_config.LISTING_LINK_SELECTOR)
        date_node = item.select_one(wrc_config.LISTING_DATE_SELECTOR)
        if link is None or date_node is None:
            logger.warning("listing_row_incomplete", extra={"partition": partition.label, "body": body.code})
            return None

        href = link["href"]
        document_url = href if href.startswith("http") else f"{wrc_config.SITE_ROOT}{href}"
        identifier = collapse_whitespace(link.get_text(" "))
        reference = item.select_one(wrc_config.LISTING_REFERENCE_SELECTOR)
        description = item.select_one(wrc_config.LISTING_DESCRIPTION_SELECTOR)

        try:
            # the date comes from the row, never from the url: a 30/01/2024 decision sits under /2024/february/
            decision_date = parse_date(date_node.get_text(strip=True))
        except ValueError:
            logger.warning("listing_row_bad_date", extra={"identifier": identifier, "partition": partition.label})
            return None

        return DecisionRecordDTO(
            identifier=collapse_whitespace(reference.get_text(" ")) if reference else identifier,
            body_code=body.code,
            body_name=body.name,
            title=identifier,
            description=collapse_whitespace(description.get_text(" ")) if description else "",
            decision_date=decision_date,
            source_url=document_url,
            document_url=document_url,
            partition_date=partition.label,
            content_type=self._guess_content_type(document_url),
            source_name=source_name,
        )

    def _guess_content_type(self, url: str) -> str:
        # used because the listing only gives us a link; the real header is checked again on download
        extension = url.rsplit(".", 1)[-1].lower() if "." in url.rsplit("/", 1)[-1] else ""
        return _CONTENT_TYPE_BY_EXTENSION.get(extension, "text/html")
