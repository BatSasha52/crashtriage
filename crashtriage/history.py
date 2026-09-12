from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BlameEntry:
    sha: str
    author: str
    summary: str
    line_number: int

    @property
    def short_sha(self) -> str:
        return self.sha[:8]


@dataclass
class FileHistory:
    path: str
    blame: list[BlameEntry] = field(default_factory=list)


class HistoryProvider:
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path

    def _run_git(self, args: list[str]) -> tuple[int, str, str]:
        proc = subprocess.run(
            ["git", "-C", str(self.repo_path), *args],
            capture_output=True,
            text=True,
        )
        return proc.returncode, proc.stdout, proc.stderr

    def history_for(self, file_path: Path, line: int, radius: int = 4) -> FileHistory:
        relative = file_path.relative_to(self.repo_path).as_posix()

        start = max(1, line - radius)
        end = line + radius

        code, stdout, stderr = self._run_git(
            ["blame", "-L", f"{start},{end}", "--line-porcelain", "--", relative]
        )

        history = FileHistory(path=relative)
        if code != 0:
            return history

        current_sha = ""
        current_author = ""
        current_summary = ""
        current_line = 0

        for raw_line in stdout.splitlines():
            if raw_line.startswith("\t"):
                history.blame.append(
                    BlameEntry(
                        sha=current_sha,
                        author=current_author,
                        summary=current_summary,
                        line_number=current_line,
                    )
                )
                continue

            parts = raw_line.split(" ", 1)
            key = parts[0]

            if len(key) == 40 and all(c in "0123456789abcdef" for c in key):
                current_sha = key
                current_line = int(raw_line.split(" ")[2])
            elif key == "author":
                current_author = parts[1] if len(parts) > 1 else ""
            elif key == "summary":
                current_summary = parts[1] if len(parts) > 1 else ""

        return history