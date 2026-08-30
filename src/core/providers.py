from dataclasses import dataclass

from src.application.services.document_storage_service import DocumentStorageService
from src.application.services.ingestion_service import IngestionService
from src.application.services.partition_planning_service import PartitionPlanningService
from src.application.services.run_summary_service import RunSummaryService
from src.application.services.sources.source_registry import SourceRegistry
from src.application.services.sources.workplace_relations.wrc_content_extractor import WrcContentExtractor
from src.application.services.sources.workplace_relations.wrc_listing_parser import WrcListingParser
from src.application.services.sources.workplace_relations.wrc_source_service import WrcSourceService
from src.application.services.transformation_service import TransformationService
from src.application.services_interfaces.ingestion_service_interface import IIngestionService
from src.application.services_interfaces.partition_planning_service_interface import IPartitionPlanningService
from src.application.services_interfaces.transformation_service_interface import ITransformationService
from src.core.config import Settings, get_settings
from src.infrastructure.database.mongo_connection_provider import MongoConnectionProvider
from src.infrastructure.object_storage.object_store import ObjectStore, build_minio_client
from src.infrastructure.object_storage_interfaces.object_store_interface import IObjectStore
from src.infrastructure.repositories.decision_metadata_repository import DecisionMetadataRepository
from src.infrastructure.repositories_interfaces.decision_metadata_repository_interface import IDecisionMetadataRepository
from src.infrastructure.scraping.crawl_runner import CrawlRunner


@dataclass(frozen=True, slots=True)
class PipelineServices:
    settings: Settings
    mongo: MongoConnectionProvider
    planning: IPartitionPlanningService
    ingestion: IIngestionService
    transformation: ITransformationService
    landing_object_store: IObjectStore
    curated_object_store: IObjectStore
    landing_repository: IDecisionMetadataRepository
    curated_repository: IDecisionMetadataRepository

    def prepare_storage(self) -> None:
        # used at startup so buckets and indexes exist before the first partition runs
        for store in (self.landing_object_store, self.curated_object_store):
            store.ensure_bucket()
        for repository in (self.landing_repository, self.curated_repository):
            repository.ensure_indexes()

    def close(self) -> None:
        # used on shutdown so a cli run does not leave sockets open
        self.mongo.close()


def build_source_registry() -> SourceRegistry:
    return SourceRegistry([WrcSourceService(WrcListingParser(), WrcContentExtractor())])


def build_services(settings: Settings | None = None) -> PipelineServices:
    # the single place an interface is bound to a class; swapping a backend is a diff here and nowhere else
    settings = settings or get_settings()

    mongo = MongoConnectionProvider(settings)
    minio_client = build_minio_client(settings)
    database = mongo.get_database()

    landing_repository = DecisionMetadataRepository(database, settings.landing_collection, settings)
    curated_repository = DecisionMetadataRepository(database, settings.curated_collection, settings)
    landing_object_store = ObjectStore(minio_client, settings.landing_bucket, settings)
    curated_object_store = ObjectStore(minio_client, settings.curated_bucket, settings)

    # one storage service class, built twice: once over the landing pair, once over the curated pair
    landing_storage = DocumentStorageService(landing_repository, landing_object_store)
    curated_storage = DocumentStorageService(curated_repository, curated_object_store)

    source_registry = build_source_registry()
    planning = PartitionPlanningService(settings)
    summaries = RunSummaryService()

    return PipelineServices(
        settings=settings,
        mongo=mongo,
        planning=planning,
        ingestion=IngestionService(
            source_registry=source_registry,
            crawl_runner=CrawlRunner(settings),
            storage_service=landing_storage,
            planning_service=planning,
            run_summary_service=summaries,
            settings=settings,
        ),
        transformation=TransformationService(
            source_registry=source_registry,
            landing_repository=landing_repository,
            landing_object_store=landing_object_store,
            storage_service=curated_storage,
            planning_service=planning,
            run_summary_service=summaries,
            settings=settings,
        ),
        landing_object_store=landing_object_store,
        curated_object_store=curated_object_store,
        landing_repository=landing_repository,
        curated_repository=curated_repository,
    )
