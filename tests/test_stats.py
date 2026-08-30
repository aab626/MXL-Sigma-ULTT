import pytest

from core.stats import compute


def test_compute_known_values():
    stats = compute([10.0, 20.0, 30.0])
    assert stats.minimum == 10.0
    assert stats.maximum == 30.0
    assert stats.average == 20.0
    assert stats.stddev == pytest.approx(8.16, abs=0.01)


def test_compute_single_ping():
    stats = compute([42.0])
    assert stats.minimum == 42.0
    assert stats.maximum == 42.0
    assert stats.average == 42.0
    assert stats.stddev == 0.0


def test_compute_empty_raises():
    with pytest.raises(ValueError):
        compute([])
