from core.gslist import GameServer
from core.output import collect, render_report


def _server(name="GS1", label="US West [us]", cc="us", ip="192.0.2.1"):
    return GameServer(name=name, label=label, country_code=cc, ip=ip)


def _sample_results():
    return [
        collect(_server("GS1", "US West [us]"), [20.0, 22.0, 24.0]),
        collect(_server("GS2", "EU Central [de]", cc="de", ip="192.0.2.2"), [None, None]),
        collect(
            _server("GS3", "Asia SG [sg]", cc="sg", ip="192.0.2.3"),
            [50.0, 60.0, None, 70.0],
        ),
    ]


def test_collect_all_successful():
    result = collect(_server(), [10.0, 12.0])
    assert not result.skipped
    assert result.lost == 0
    assert result.stats.minimum == 10.0
    assert result.stats.maximum == 12.0
    assert result.stats.average == 11.0


def test_collect_all_failed_is_skipped():
    result = collect(_server(), [None, None])
    assert result.skipped
    assert result.stats is None
    assert result.lost == 2


def test_collect_partial_uses_successful_only():
    result = collect(_server(), [10.0, None, 20.0])
    assert not result.skipped
    assert result.lost == 1
    assert result.stats.minimum == 10.0
    assert result.stats.maximum == 20.0
    assert result.stats.average == 15.0


def test_report_header_mentions_tries():
    report = render_report(_sample_results(), 4)
    assert "Ping Information (4 tries)" in report


def test_report_keeps_server_order():
    report = render_report(_sample_results(), 4)
    assert report.index("GS1") < report.index("GS2") < report.index("GS3")


def test_report_marks_fully_failed_server():
    report = render_report(_sample_results(), 4)
    assert "SKIPPED (no reply)" in report


def test_report_notes_partial_loss():
    report = render_report(_sample_results(), 4)
    assert "1/4 replies lost" in report


def test_report_flags_unstable_stddev():
    results = [
        collect(_server("GS1", "Stable [us]"), [20.0, 21.0, 22.0]),
        collect(_server("GS2", "Jittery [de]", cc="de"), [10.0, 45.0]),
    ]
    report = render_report(results, 4)
    assert "unstable" in report.split("GS2", 1)[1]
    assert "unstable" not in report.split("GS2", 1)[0].split("Ping Information", 1)[1]


def test_report_formats_one_decimal():
    report = render_report(_sample_results(), 4)
    assert "Avg: 22.0" in report
    assert "StdDev: 8.2" in report


def test_top_section_sorted_excludes_skipped():
    results = [
        collect(_server(f"GS{i}", f"S {i} [us]", ip=f"192.0.2.{i}"), [float(10 * i)] * 2)
        for i in range(1, 7)
    ]
    results.append(collect(_server("GS9", "Dead [xx]", cc=""), [None, None]))
    report = render_report(results, 4)
    assert "Top 5 average pings:" in report
    top = report.split("Top 5 average pings:", 1)[1]
    assert "GS9" not in top
    places = [line for line in top.splitlines() if line and line[0].isdigit()]
    assert len(places) == 5
    assert places[0].startswith("1. GS1")
    assert places[-1].startswith("5. GS5")


def test_top_heading_shows_actual_count():
    report = render_report(_sample_results(), 4)
    assert "Top 2 average pings:" in report


def test_all_skipped_has_no_top_section():
    results = [collect(_server("GS1"), [None, None])]
    report = render_report(results, 4)
    assert "Top" not in report
