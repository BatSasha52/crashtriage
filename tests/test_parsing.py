import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crashtriage.parsing import CrashLogParser


def test_parses_all_demo_crash_logs():
    parser = CrashLogParser()
    demo_crashes = Path(__file__).resolve().parent.parent.parent / "demo-crashes"
    reports = parser.parse_path(demo_crashes)

    assert len(reports) == 6


def test_spawner_crash_has_two_frames():
    parser = CrashLogParser()
    demo_crashes = Path(__file__).resolve().parent.parent.parent / "demo-crashes"
    reports = parser.parse_path(demo_crashes)

    spawner_reports = [r for r in reports if r.identifier.startswith("spawner")]
    assert len(spawner_reports) == 4

    for report in spawner_reports:
        assert len(report.frames) == 2
        assert report.frames[0].function == "AEnemySpawner::SpawnWave()"


def test_unparseable_log_has_no_frames():
    parser = CrashLogParser()
    demo_crashes = Path(__file__).resolve().parent.parent.parent / "demo-crashes"
    reports = parser.parse_path(demo_crashes)

    unparsed = next(r for r in reports if r.identifier == "unparseable")
    assert unparsed.frames == []