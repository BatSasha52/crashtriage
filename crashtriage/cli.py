from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .clustering import cluster_crashes
from .history import FileHistory, HistoryProvider
from .llm import build_prompt, call_gemini
from .parsing import CrashLogParser
from .report import write_reports
from .source import SourceResolver


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crashtriage",
        description="Triage crash logs using source context, git history and an LLM.",
    )
    parser.add_argument("--repo", required=True, help="path to the source repository")
    parser.add_argument("--crashes", required=True, help="crash log file or directory")
    parser.add_argument("--out", default="triage-reports", help="output directory for reports")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("error: GEMINI_API_KEY is not set", file=sys.stderr)
        return 2

    repo_path = Path(args.repo)
    crash_path = Path(args.crashes)
    output_path = Path(args.out)

    if not repo_path.exists():
        print(f"error: repo path does not exist: {repo_path}", file=sys.stderr)
        return 2

    if not crash_path.exists():
        print(f"error: crash path does not exist: {crash_path}", file=sys.stderr)
        return 2

    parser = CrashLogParser()
    reports = parser.parse_path(crash_path)
    usable = [r for r in reports if r.frames]

    if not usable:
        print("error: no crash logs contained a recognisable stack trace", file=sys.stderr)
        return 3

    print(f"parsed {len(reports)} crash logs, {len(usable)} had a usable trace")

    clusters = cluster_crashes(usable)
    print(f"grouped into {len(clusters)} clusters")

    resolver = SourceResolver(repo_path)
    provider = HistoryProvider(repo_path)

    evidence = []
    for cluster in clusters:
        frame = cluster.crashes[0].frames[0]
        context = resolver.context_for(frame.file, frame.line)

        if context.found:
            history = provider.history_for(context.resolved_path, frame.line)
        else:
            history = FileHistory(path="unknown")

        prompt = build_prompt(cluster, context, history.blame)
        analysis = call_gemini(api_key, prompt)

        print(f"  {cluster.identifier}: {cluster.count} crashes, severity {analysis.severity}")
        evidence.append((cluster, context, history, analysis))

    index_path = write_reports(evidence, output_path)
    print(f"wrote {len(evidence)} report(s) to {output_path}")
    print(f"index: {index_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())