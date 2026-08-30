from dagster import Definitions

from src.presentation.orchestration.assets.curated_documents_asset import curated_documents
from src.presentation.orchestration.assets.landing_documents_asset import landing_documents
from src.presentation.orchestration.resources.pipeline_services_resource import PipelineServicesResource

# the orchestrated path 
defs = Definitions(
    assets=[landing_documents, curated_documents],
    resources={"pipeline_services": PipelineServicesResource()},
)
