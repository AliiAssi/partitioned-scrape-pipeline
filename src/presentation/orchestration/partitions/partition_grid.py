from dagster import (
    DailyPartitionsDefinition,
    MonthlyPartitionsDefinition,
    MultiPartitionsDefinition,
    StaticPartitionsDefinition,
    WeeklyPartitionsDefinition,
)

from src.application.services.sources.workplace_relations.wrc_config import WRC_BODIES
from src.core.config import get_settings

PERIOD_DIMENSION = "period"
BODY_DIMENSION = "body"

# Deliberately a constant, not a setting. It is the origin of every Dagster partition key, so moving
# it renames all of them and detaches the existing materialisation history. 2015 is the year the
# Workplace Relations Act folded the older tribunals into the WRC.
GRID_START_DATE = "2015-01-01"

_PERIOD_DEFINITION_BY_SIZE = {
    "daily": DailyPartitionsDefinition,
    "weekly": WeeklyPartitionsDefinition,
    "monthly": MonthlyPartitionsDefinition,
}


def build_decision_partitions(partition_size: str | None = None) -> MultiPartitionsDefinition:
    # the grid is (period x body): one slow body cannot stall the others, and a retry is one cell
    size = partition_size or get_settings().partition_size
    return MultiPartitionsDefinition(
        {
            PERIOD_DIMENSION: _PERIOD_DEFINITION_BY_SIZE[size](start_date=GRID_START_DATE),
            BODY_DIMENSION: StaticPartitionsDefinition([body.code for body in WRC_BODIES]),
        }
    )


decision_partitions = build_decision_partitions()
