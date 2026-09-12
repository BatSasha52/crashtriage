import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crashtriage.parsing import CrashLogParser
from crashtriage.clustering import cluster_crashes

DEMO_CRASHES = Path(__file__).resolve().parent.parent.parent / "demo-crashes"


def test_near_identical_spawner_crashes_form_one_cluster():
    parser = CrashLogParser()
    reports = parser.parse_path(DEMO_CRASHES)
    usable = [r for r in reports if r.frames]

    clusters = cluster_crashes(usable)

    spawner_cluster = next(c for c in clusters if "spawner_crash_1" in c.crash_identifiers())
    assert spawner_cluster.count == 4
    assert "spawner_crash_variant" in spawner_cluster.crash_identifiers()


def test_unrelated_crash_stays_in_its_own_cluster():
    parser = CrashLogParser()
    reports = parser.parse_path(DEMO_CRASHES)
    usable = [r for r in reports if r.frames]

    clusters = cluster_crashes(usable)

    save_cluster = next(c for c in clusters if "save_crash" in c.crash_identifiers())
    assert save_cluster.count == 1


def test_exactly_two_clusters_from_five_usable_crashes():
    parser = CrashLogParser()
    reports = parser.parse_path(DEMO_CRASHES)
    usable = [r for r in reports if r.frames]

    clusters = cluster_crashes(usable)

    assert len(clusters) == 2