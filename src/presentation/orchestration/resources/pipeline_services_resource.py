from functools import lru_cache

from dagster import ConfigurableResource

from src.core.config import get_settings
from src.core.logging import configure_logging
from src.core.providers import PipelineServices, build_services


@lru_cache(maxsize=1)
def _bootstrapped_services() -> PipelineServices:
    # used so every asset in a process shares one dependency graph, built the same way the cli builds it
    settings = get_settings()
    configure_logging(settings.log_level)
    services = build_services(settings)
    services.prepare_storage()
    return services

# the bridge to the services
class PipelineServicesResource(ConfigurableResource):
    source_name: str = "workplace_relations"

    def get_services(self) -> PipelineServices:
        # used for handing assets their services instead of letting them construct anything
        return _bootstrapped_services()
