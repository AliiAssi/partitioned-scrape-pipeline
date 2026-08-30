from datetime import date

import pytest

from src.application.dto.base.content_hash import ContentHash
from src.application.dto.base.decision_record_dto import DecisionRecordDTO
from src.application.dto.base.object_key import ObjectKey
from src.application.services.document_storage_service import DocumentStorageService
from tests.fakes import FakeMetadataRepository, FakeObjectStore

KEY = ObjectKey("landing/wrc/2024-01/adj-00047352.html")


@pytest.fixture
def record() -> DecisionRecordDTO:
    return DecisionRecordDTO(
        identifier="ADJ-00047352",
        body_code="wrc",
        body_name="Workplace Relations Commission",
        title="ADJ-00047352",
        description="Car Valet V Motor Garage",
        decision_date=date(2024, 1, 31),
        source_url="https://example.test/adj-00047352.html",
        document_url="https://example.test/adj-00047352.html",
        partition_date="2024-01",
        content_type="text/html",
        source_name="workplace_relations",
    )


@pytest.fixture
def backends():
    repository, store = FakeMetadataRepository(), FakeObjectStore()
    return DocumentStorageService(repository, store), repository, store


def test_a_first_write_stores_the_object_and_its_metadata(backends, record):
    service, repository, store = backends

    outcome = service.store_document_if_content_changed(record, b"<html>one</html>", KEY)

    assert outcome.was_written
    assert store.put_calls == 1
    assert repository.documents[record.storage_id].file_hash == str(outcome.content_hash)


def test_identical_content_is_never_written_twice(backends, record):
    service, repository, store = backends
    payload = b"<html>one</html>"

    service.store_document_if_content_changed(record, payload, KEY)
    second = service.store_document_if_content_changed(record, payload, KEY)

    assert not second.was_written
    assert store.put_calls == 1
    assert len(repository.documents) == 1


def test_changed_content_is_written_again(backends, record):
    service, _, store = backends

    first = service.store_document_if_content_changed(record, b"<html>one</html>", KEY)
    second = service.store_document_if_content_changed(record, b"<html>two</html>", KEY)

    assert second.was_written
    assert first.content_hash != second.content_hash
    assert store.put_calls == 2


def test_content_differing_only_in_volatile_markup_counts_as_unchanged(backends, record):
    service, repository, store = backends
    first_render = b"<html><!-- Elapsed time: 0 -->decision</html>"
    second_render = b"<html><!-- Elapsed time: 0.0156031 -->decision</html>"
    stable = b"<html>decision</html>"

    service.store_document_if_content_changed(record, first_render, KEY, comparison_content=stable)
    second = service.store_document_if_content_changed(record, second_render, KEY, comparison_content=stable)

    assert not second.was_written
    assert store.objects[KEY.value] == first_render
    # the stored hash still describes the bytes on disk, not the fingerprint the check used
    assert repository.documents[record.storage_id].file_hash == str(ContentHash.of_bytes(first_render))
