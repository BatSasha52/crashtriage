import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crashtriage.source import SourceResolver

DEMO_GAME = Path(__file__).resolve().parent.parent.parent / "demo-game"


def test_indexes_the_one_tracked_file():
    resolver = SourceResolver(DEMO_GAME)
    assert resolver.indexed_file_count() == 1


def test_resolves_a_windows_build_path_to_the_local_file():
    resolver = SourceResolver(DEMO_GAME)
    resolved, note = resolver.resolve(r"D:\build\Source\Game\EnemySpawner.cpp")

    assert resolved is not None
    assert resolved.name == "EnemySpawner.cpp"


def test_extracts_the_crashing_line_and_its_surroundings():
    resolver = SourceResolver(DEMO_GAME)
    context = resolver.context_for(r"D:\build\Source\Game\EnemySpawner.cpp", 9)

    assert context.found
    assert any("EnemyPool[Index]" in line for line in context.lines)