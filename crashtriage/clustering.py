from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from .parsing import CrashReport

HEX_PATTERN = re.compile(r"0x[0-9a-fA-F]+")


@dataclass
class CrashCluster:
    identifier: str
    crashes: list[CrashReport] = field(default_factory=list)
    signature: str = ""

    @property
    def count(self) -> int:
        return len(self.crashes)

    def crash_identifiers(self) -> list[str]:
        return [c.identifier for c in self.crashes]


def normalise_message(message: str) -> str:
    cleaned = HEX_PATTERN.sub("0xADDR", message)
    return " ".join(cleaned.split()).lower()


def cluster_key(report: CrashReport, depth: int = 3) -> str:
    frame_part = " > ".join(f.signature() for f in report.frames[:depth])
    message_part = normalise_message(report.message)
    return f"{message_part}||{frame_part}"


def similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def cluster_crashes(reports: list[CrashReport], threshold: float = 0.75) -> list[CrashCluster]:
    clusters: list[CrashCluster] = []

    for report in reports:
        key = cluster_key(report)

        best_cluster = None
        best_score = 0.0

        for cluster in clusters:
            score = similarity(key, cluster.signature)
            if score > best_score:
                best_score = score
                best_cluster = cluster

        if best_cluster is not None and best_score >= threshold:
            best_cluster.crashes.append(report)
        else:
            clusters.append(
                CrashCluster(
                    identifier=f"cluster-{len(clusters) + 1:03d}",
                    crashes=[report],
                    signature=key,
                )
            )

    return clusters