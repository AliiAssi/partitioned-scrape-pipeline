from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceBody:
    code: str
    name: str
    external_id: str
