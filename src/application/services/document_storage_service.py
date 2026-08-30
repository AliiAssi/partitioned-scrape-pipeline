from src.application.dto.base.content_hash import ContentHash
from src.application.dto.base.decision_record_dto import DecisionRecordDTO
from src.application.dto.base.object_key import ObjectKey
from src.application.dto.base.storage_outcome_dto import StorageOutcomeDTO
from src.application.services_interfaces.document_storage_service_interface import IDocumentStorageService
from src.infrastructure.object_storage_interfaces.object_store_interface import IObjectStore
from src.infrastructure.repositories_interfaces.decision_metadata_repository_interface import IDecisionMetadataRepository


class DocumentStorageService(IDocumentStorageService):
    def __init__(self, metadata_repository: IDecisionMetadataRepository, object_store: IObjectStore) -> None:
        # one class, registered twice: once against the landing pair, once against the curated pair
        self._metadata_repository = metadata_repository
        self._object_store = object_store

    def store_document_if_content_changed(
        self,
        record: DecisionRecordDTO,
        content: bytes,
        object_key: ObjectKey,
        comparison_content: bytes | None = None,
    ) -> StorageOutcomeDTO:
        # idempotency lives here and nowhere else: a rerun that finds the same content writes nothing
        content_hash = ContentHash.of_bytes(content)
        # the site stamps a render time into every page, so the comparison runs on a normalised copy
        # while file_hash keeps describing the bytes we actually stored
        fingerprint = ContentHash.of_bytes(comparison_content) if comparison_content is not None else content_hash
        existing = self._metadata_repository.find_by_identifier_and_body(record.identifier, record.body_code)
        if existing is not None and existing.comparison_fingerprint == fingerprint and existing.file_path == object_key.value:
            return StorageOutcomeDTO.unchanged(object_key, content_hash, record.identifier)

        # object first, metadata second: a crash between them leaves an orphan file, never a dangling pointer
        self._object_store.put_object(object_key, content, record.content_type)
        self._metadata_repository.upsert(record.with_storage(object_key, content_hash, fingerprint))
        return StorageOutcomeDTO.written(object_key, content_hash, record.identifier)
