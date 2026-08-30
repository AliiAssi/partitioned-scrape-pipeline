from src.application.exceptions import UnknownSourceError
from src.application.services_interfaces.source_service_interface import ISourceService


class SourceRegistry:
    def __init__(self, services: list[ISourceService]) -> None:
        self._services = {service.name: service for service in services}

    def get(self, source_name: str) -> ISourceService:
        # used for the only place a configured source name becomes a class
        try:
            return self._services[source_name]
        except KeyError:
            raise UnknownSourceError(f"no source service registered for {source_name!r}") from None

    def available_names(self) -> list[str]:
        return sorted(self._services)
