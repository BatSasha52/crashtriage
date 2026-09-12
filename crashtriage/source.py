from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SourceContext:
    resolved_path: Path | None
    resolution_note: str = ""
    lines: list[str] = None
    start_line: int = 0

    def __post_init__(self):
        if self.lines is None:
            self.lines = []

    @property
    def found(self) -> bool:
        return self.resolved_path is not None and bool(self.lines)


class SourceResolver:
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self._index: dict[str, list[Path]] = {}
        self._build_index()

    def _build_index(self) -> None:
        proc = subprocess.run(
            ["git", "-C", str(self.repo_path), "ls-files"],
            capture_output=True,
            text=True,
        )
        for relative in proc.stdout.splitlines():
            relative = relative.strip()
            if not relative:
                continue
            path = self.repo_path / relative
            self._index.setdefault(os.path.basename(relative), []).append(path)

    def indexed_file_count(self) -> int:
        return sum(len(paths) for paths in self._index.values())

    def resolve(self, crash_path: str) -> tuple[Path | None, str]:
        basename = os.path.basename(crash_path.replace("\\", "/"))
        candidates = self._index.get(basename, [])

        if not candidates:
            return None, "no file with that name in the repository"

        return candidates[0], "matched by filename"

    def context_for(self, file: str, line: int, radius: int = 4) -> SourceContext:
        resolved, note = self.resolve(file)

        if resolved is None:
            return SourceContext(resolved_path=None, resolution_note=note)

        all_lines = resolved.read_text(encoding="utf-8", errors="replace").splitlines()

        start = max(0, line - 1 - radius)
        end = min(len(all_lines), line + radius)

        return SourceContext(
            resolved_path=resolved,
            resolution_note=note,
            lines=all_lines[start:end],
            start_line=start + 1,
        )