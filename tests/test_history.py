import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crashtriage.history import HistoryProvider

DEMO_GAME = Path(__file__).resolve().parent.parent.parent / "demo-game"


def test_blame_identifies_the_commit_that_changed_the_crashing_line():
    provider = HistoryProvider(DEMO_GAME)
    file_path = DEMO_GAME / "Source" / "Game" / "EnemySpawner.cpp"

    history = provider.history_for(file_path, 3)

    line_three = next(entry for entry in history.blame if entry.line_number == 3)
    assert "difficulty multiplier" in line_three.summary