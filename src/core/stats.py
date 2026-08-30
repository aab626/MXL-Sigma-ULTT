import statistics
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Stats:
    minimum: float
    maximum: float
    average: float
    stddev: float


def compute(pings: Sequence[float]) -> Stats:
    if not pings:
        raise ValueError("cannot compute stats for an empty ping list")
    return Stats(
        minimum=min(pings),
        maximum=max(pings),
        average=statistics.mean(pings),
        stddev=statistics.pstdev(pings),
    )
