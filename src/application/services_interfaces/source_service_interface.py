from abc import ABC, abstractmethod

from src.application.dto.base.date_partition import DatePartition
from src.application.dto.base.decision_record_dto import DecisionRecordDTO
from src.application.dto.base.source_body import SourceBody
from src.application.dto.ingestion.listing_page_dto import ListingPageDTO
from src.application.dto.ingestion.listing_request_dto import ListingRequestDTO


class ISourceService(ABC):
    name: str

    @abstractmethod
    def list_available_bodies(self) -> list[SourceBody]:
        # used for the left-hand body filter, and for the partition grid
        ...

    @abstractmethod
    def build_listing_request(self, body: SourceBody, partition: DatePartition, page_number: int) -> ListingRequestDTO:
        # used for turning a partition into the one url that lists its records
        ...

    @abstractmethod
    def parse_listing_page(self, payload: bytes, body: SourceBody, partition: DatePartition) -> ListingPageDTO:
        # used for reading result rows out of a search page
        ...

    @abstractmethod
    def build_document_request(self, record: DecisionRecordDTO) -> ListingRequestDTO:
        # used for turning a record into the request that fetches its document
        ...

    @abstractmethod
    def extract_relevant_content(self, payload: bytes, content_type: str) -> bytes:
        # used for stripping site chrome off an html document during transformation
        ...

    @abstractmethod
    def normalise_for_comparison(self, payload: bytes, content_type: str) -> bytes:
        # used for blanking the per-request noise a site stamps into its pages, so hashes are stable between runs
        ...
