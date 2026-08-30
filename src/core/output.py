"""Report rendering for the terminal.

collect() turns a server's raw ping list into a ServerResult and
render_report() formats the full report as a string. Nothing here prints
or touches the network, which keeps rendering easy to test.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from core.gslist import GameServer
from core.stats import Stats, compute


@dataclass(frozen=True)
class ServerResult:
    server: GameServer
    pings: tuple[float | None, ...]
    stats: Stats | None
    lost: int

    @property
    def skipped(self) -> bool:
        return self.stats is None


def collect(server: GameServer, pings: Iterable[float | None]) -> ServerResult:
    entries = tuple(pings)
    successful = [value for value in entries if value is not None]
    return ServerResult(
        server=server,
        pings=entries,
        stats=compute(successful) if successful else None,
        lost=len(entries) - len(successful),
    )


def render_report(
    results: Sequence[ServerResult],
    tries: int,
    *,
    top_n: int = 5,
    stddev_warn: float = 10.0,
) -> str:
    lines = [
        f"Ping Information ({tries} tries)",
        "Less Average Ping (Avg) is better, less Standard Deviation (StdDev) is better.",
        f"A StdDev above {stddev_warn:g} means the measurement was not stable.",
        "",
    ]

    name_width = max((len(result.server.name) for result in results), default=0) + 2
    label_width = max((len(result.server.label) for result in results), default=0) + 4

    for result in results:
        lines.append(_render_row(result, name_width, label_width, stddev_warn))

    ranked = sorted(
        (result for result in results if not result.skipped),
        key=lambda result: result.stats.average,
    )
    if ranked:
        count = min(top_n, len(ranked))
        lines.append("")
        lines.append(f"Top {count} average pings:")
        for place, result in enumerate(ranked[:count], start=1):
            lines.append(
                f"{place}. {result.server.name} {result.server.label} "
                f"{result.stats.average:.1f} ms"
            )

    return "\n".join(lines)


def _render_row(
    result: ServerResult,
    name_width: int,
    label_width: int,
    stddev_warn: float,
) -> str:
    left = result.server.name.ljust(name_width) + _dotted(result.server.label, label_width)
    if result.stats is None:
        return left + "SKIPPED (no reply)"

    stats = result.stats
    cells = [
        f"Min: {stats.minimum:.1f}",
        f"Max: {stats.maximum:.1f}",
        f"Avg: {stats.average:.1f}",
        f"StdDev: {stats.stddev:.1f}",
    ]
    row = left + "  ".join(cells)

    notes = []
    if result.lost:
        notes.append(f"{result.lost}/{len(result.pings)} replies lost")
    if stats.stddev > stddev_warn:
        notes.append("unstable")
    if notes:
        row += "  (" + "; ".join(notes) + ")"
    return row


def _dotted(label: str, width: int) -> str:
    return label + " " + "." * max(2, width - len(label)) + " "
