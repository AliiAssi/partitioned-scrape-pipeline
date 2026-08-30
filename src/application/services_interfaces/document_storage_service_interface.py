from abc import ABC, abstractmethod

from src.application.dto.base.decision_record_dto import DecisionRecordDTO
from src.application.dto.base.object_key import ObjectKey
from src.application.dto.base.storage_outcome_dto import StorageOutcomeDTO


class IDocumentStorageService(ABC):
    @abstractmethod
    def store_document_if_content_changed(
        self,
        record: DecisionRecordDTO,
        content: bytes,
        object_key: ObjectKey,
        comparison_content: bytes | None = None,
    ) -> StorageOutcomeDTO:
        # used by both stages, which is the whole reason it is one method and not two
        ...
