from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .errors import InputError

DEFAULT_FRAME_PATTERNS = [
    r"!(?P<function>[^\s\[\]]+)\s*\[(?P<file>[^\[\]]+?):(?P<line>\d+)\]",
]

DEFAULT_MESSAGE_PATTERNS = [
    r"(?i)^\s*(?P<message>(?:fatal|unhandled|assertion|error)[^\n]*)",
]


@dataclass
class StackFrame:
    index: int
    file: str
    line: int
    function: str = ""

    @property
    def basename(self) -> str:
        return os.path.basename(self.file.replace("\\", "/"))

    def signature(self) -> str:
        if self.function:
            return f"{self.basename}:{self.function}"
        return f"{self.basename}:{self.line}"

    def location(self) -> str:
        return f"{self.file}:{self.line}"


@dataclass
class CrashReport:
    identifier: str
    raw_text: str
    message: str = ""
    frames: list[StackFrame] = field(default_factory=list)

    @property
    def top_frame(self) -> StackFrame | None:
        return self.frames[0] if self.frames else None

    def short_description(self) -> str:
        if self.message:
            return self.message
        if self.top_frame is not None:
            return f"Crash in {self.top_frame.signature()}"
        return "Unparsed crash"


class CrashLogParser:
    def __init__(self, frame_patterns=None, message_patterns=None):
        raw_frames = frame_patterns or DEFAULT_FRAME_PATTERNS
        raw_messages = message_patterns or DEFAULT_MESSAGE_PATTERNS

        self.frame_patterns = [re.compile(p) for p in raw_frames]
        self.message_patterns = [re.compile(p) for p in raw_messages]

    def parse_text(self, text: str, identifier: str) -> CrashReport:
        report = CrashReport(identifier=identifier, raw_text=text)

        for raw_line in text.splitlines():
            if not report.message:
                for pattern in self.message_patterns:
                    match = pattern.search(raw_line)
                    if match:
                        report.message = match.group("message").strip()
                        break

            for pattern in self.frame_patterns:
                match = pattern.search(raw_line)
                if match:
                    groups = match.groupdict()
                    report.frames.append(
                        StackFrame(
                            index=len(report.frames),
                            file=groups.get("file", "").strip(),
                            line=int(groups.get("line", "0")),
                            function=(groups.get("function") or "").strip(),
                        )
                    )
                    break

        return report

    def parse_path(self, path: Path) -> list[CrashReport]:
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace")
            return [self.parse_text(text, path.stem)]

        if not path.is_dir():
            raise InputError(f"crash input path does not exist: {path}")

        files = sorted(p for p in path.glob("*.log") if p.is_file())
        return [
            self.parse_text(f.read_text(encoding="utf-8", errors="replace"), f.stem)
            for f in files
        ]