from datetime import date

from dagster import AssetExecutionContext, MaterializeResult, asset

from src.application.dto.base.date_partition import DatePartition
from src.core.providers import PipelineServices
from src.presentation.orchestration.partitions import partition_grid as grid
from src.presentation.orchestration.resources.pipeline_services_resource import PipelineServicesResource


def resolve_partition(context: AssetExecutionContext, services: PipelineServices) -> tuple[DatePartition, str]:
    dimensions = context.partition_key.keys_by_dimension
    period_start = date.fromisoformat(dimensions[grid.PERIOD_DIMENSION])
    return services.planning.partition_starting_at(period_start), dimensions[grid.BODY_DIMENSION]


@asset(partitions_def=grid.decision_partitions, group_name="landing", description="Raw decisions and metadata as served by the source")
def landing_documents(context: AssetExecutionContext, pipeline_services: PipelineServicesResource) -> MaterializeResult:
    # used for materialising one (month, body) cell of the ingest stage
    services = pipeline_services.get_services()
    partition, body_code = resolve_partition(context, services)
    result = services.ingestion.ingest_single_partition(partition, body_code, pipeline_services.source_name)
    return MaterializeResult(metadata=result.as_log_fields())
