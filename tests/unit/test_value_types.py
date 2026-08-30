from datetime import date

import pytest

from src.application.dto.base.content_hash import ContentHash
from src.application.dto.base.date_partition import DatePartition


def test_a_hash_round_trips_through_its_stored_form():
    original = ContentHash.of_bytes(b"decision text")
    assert ContentHash.from_stored(str(original)) == original


def test_a_partition_is_half_open_and_labels_its_month():
    partition = DatePartition(date(2024, 1, 1), date(2024, 2, 1), "monthly")
    assert partition.label == "2024-01"
    assert partition.last_included_day == date(2024, 1, 31)
    assert partition.contains(date(2024, 1, 31)) and not partition.contains(date(2024, 2, 1))

    with pytest.raises(ValueError):
        DatePartition(date(2024, 2, 1), date(2024, 1, 1), "monthly")
