from datetime import date, timedelta

import pytest

from src.application.services.partition_planning_service import PartitionPlanningService
from src.core.config import Settings

planner = PartitionPlanningService(Settings())


def test_a_year_splits_into_twelve_months():
    partitions = planner.plan_partitions(date(2024, 1, 1), date(2025, 1, 1), "monthly")
    assert len(partitions) == 12
    assert [p.label for p in partitions][:3] == ["2024-01", "2024-02", "2024-03"]


def test_a_ragged_range_is_covered_exactly_once():
    start, end = date(2024, 1, 15), date(2024, 4, 3)
    partitions = planner.plan_partitions(start, end, "monthly")

    assert partitions[0].start == start and partitions[-1].end == end
    day = start
    while day < end:
        assert sum(1 for p in partitions if p.contains(day)) == 1
        day += timedelta(days=1)


def test_an_inverted_range_is_rejected():
    with pytest.raises(ValueError):
        planner.plan_partitions(date(2024, 2, 1), date(2024, 1, 1), "monthly")
