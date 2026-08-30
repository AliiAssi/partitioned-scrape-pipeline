from datetime import date

import pytest
from urllib3.exceptions import HTTPError

from src.application.dto.base.content_hash import ContentHash
from src.application.dto.base.decision_record_dto import DecisionRecordDTO
from src.application.dto.base.object_key import ObjectKey
from src.core.config import Settings
from src.infrastructure.database.mongo_connection_provider import MongoConnectionProvider
from src.infrastructure.object_storage.object_store import ObjectStore, build_minio_client
from src.infrastructure.repositories.decision_metadata_repository import DecisionMetadataRepository

COLLECTION = "integration_decisions"
BUCKET = "integration-tests"
settings = Settings()


@pytest.fixture(scope="module")
def repository():
    # skips rather than fails when the containers are down, so the unit suite stays runnable alone
    provider = MongoConnectionProvider(settings)
    if not provider.check_health():
        pytest.skip("mongo is not reachable; we must run docker compose up -d")
    repository = DecisionMetadataRepository(provider.get_database(), COLLECTION, settings)
    repository.ensure_indexes()
    provider.get_database()[COLLECTION].delete_many({})
    yield repository
    provider.get_database()[COLLECTION].delete_many({})
    provider.close()


@pytest.fixture(scope="module")
def object_store():
    store = ObjectStore(build_minio_client(settings), BUCKET, settings)
    try:
        store.ensure_bucket()
    except (HTTPError, ConnectionError) as error:
        pytest.skip(f"minio is not reachable at {settings.minio_endpoint}: {error}")
    return store


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


def test_a_record_survives_a_round_trip_through_mongo(repository, record):
    repository.upsert(record.with_storage(ObjectKey("landing/wrc/2024-01/adj.html"), ContentHash.of_bytes(b"one")))

    found = repository.find_by_identifier_and_body("ADJ-00047352", "wrc")
    assert found.decision_date == date(2024, 1, 31)
    assert found.file_path == "landing/wrc/2024-01/adj.html"
    assert found.comparison_fingerprint == ContentHash.of_bytes(b"one")


def test_upserting_twice_leaves_one_document(repository, record):
    repository.upsert(record.with_storage(ObjectKey("k1"), ContentHash.of_bytes(b"one")))
    repository.upsert(record.with_storage(ObjectKey("k2"), ContentHash.of_bytes(b"two")))

    assert repository.count_by_partition("2024-01", "wrc") == 1
    assert repository.find_by_identifier_and_body("ADJ-00047352", "wrc").file_path == "k2"


def test_the_date_range_query_is_half_open(repository, record):
    repository.upsert(record.with_storage(ObjectKey("k"), ContentHash.of_bytes(b"one")))

    assert len(list(repository.iterate_by_date_range(date(2024, 1, 1), date(2024, 2, 1), "wrc"))) == 1
    assert list(repository.iterate_by_date_range(date(2024, 2, 1), date(2024, 3, 1), "wrc")) == []


def test_an_object_round_trips_through_minio(object_store):
    key = ObjectKey("integration/round-trip.html")

    object_store.put_object(key, b"<html>decision</html>", "text/html")

    assert object_store.get_object(key) == b"<html>decision</html>"
    assert not object_store.object_exists(ObjectKey("integration/never-written.html"))
