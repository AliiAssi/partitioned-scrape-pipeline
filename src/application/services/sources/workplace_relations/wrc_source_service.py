from src.application.dto.base.date_partition import DatePartition
from src.application.dto.base.decision_record_dto import DecisionRecordDTO
from src.application.dto.base.source_body import SourceBody
from src.application.dto.ingestion.listing_page_dto import ListingPageDTO
from src.application.dto.ingestion.listing_request_dto import ListingRequestDTO
from src.application.services.sources.workplace_relations import wrc_config
from src.application.services.sources.workplace_relations.wrc_content_extractor import WrcContentExtractor
from src.application.services.sources.workplace_relations.wrc_listing_parser import WrcListingParser
from src.application.services_interfaces.source_service_interface import ISourceService
from src.core.constants import HTML_CONTENT_TYPES
from src.utils.date_parsing import format_site_date


class WrcSourceService(ISourceService):
    name = wrc_config.SOURCE_NAME

    def __init__(self, listing_parser: WrcListingParser, content_extractor: WrcContentExtractor) -> None:
        self._listing_parser = listing_parser
        self._content_extractor = content_extractor

    def list_available_bodies(self) -> list[SourceBody]:
        # used for the partition grid and for the --bodies flag
        return list(wrc_config.WRC_BODIES)

    def build_listing_request(self, body: SourceBody, partition: DatePartition, page_number: int) -> ListingRequestDTO:
        # the search form posts, but the response redirects to this plain get, so we skip viewstate entirely
        query = wrc_config.LISTING_QUERY_TEMPLATE.format(
            date_from=format_site_date(partition.start),
            # the site's finish filter is inclusive, while our partitions are half-open
            date_to=format_site_date(partition.last_included_day),
            body_id=body.external_id,
            page_number=page_number,
        )
        return ListingRequestDTO(url=f"{wrc_config.SEARCH_ENDPOINT}?{query}")

    def parse_listing_page(self, payload: bytes, body: SourceBody, partition: DatePartition) -> ListingPageDTO:
        # used for reading result rows; an empty page is how pagination ends
        return self._listing_parser.parse(payload, body, partition, self.name)

    def build_document_request(self, record: DecisionRecordDTO) -> ListingRequestDTO:
        # used for fetching the decision itself, which for this site is always a page on the same host
        return ListingRequestDTO(url=record.document_url)

    def extract_relevant_content(self, payload: bytes, content_type: str) -> bytes:
        # pdfs and docs are stored as they are; only html gets its chrome stripped
        if not self._is_html(content_type):
            return payload
        return self._content_extractor.extract(payload)

    def normalise_for_comparison(self, payload: bytes, content_type: str) -> bytes:
        # used only for the change check; the bytes we store are always the ones the site served
        if not self._is_html(content_type):
            return payload
        normalised = payload
        for marker in wrc_config.VOLATILE_MARKERS:
            normalised = marker.sub(b"", normalised)
        return normalised

    def _is_html(self, content_type: str) -> bool:
        # used for the same content-type test in both directions, charset parameter included
        return content_type.split(";")[0].strip().lower() in HTML_CONTENT_TYPES
