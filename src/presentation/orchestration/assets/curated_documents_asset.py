from dagster import AssetExecutionContext, MaterializeResult, asset

from src.presentation.orchestration.assets.landing_documents_asset import landing_documents, resolve_partition
from src.presentation.orchestration.partitions import partition_grid as grid
from src.presentation.orchestration.resources.pipeline_services_resource import PipelineServicesResource


@asset(
    partitions_def=grid.decision_partitions,
    deps=[landing_documents],
    group_name="curated",
    description="Cleaned documents renamed to identifier.ext",
)
def curated_documents(context: AssetExecutionContext, pipeline_services: PipelineServicesResource) -> MaterializeResult:
    # used for materialising the transform stage of the same cell, once its ingest has succeeded
    services = pipeline_services.get_services()
    partition, body_code = resolve_partition(context, services)
    result = services.transformation.transform_single_partition(partition, body_code, pipeline_services.source_name)
    return MaterializeResult(metadata=result.as_log_fields())
