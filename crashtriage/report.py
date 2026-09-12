from __future__ import annotations

from pathlib import Path


def render_cluster_report(cluster, context, history, analysis) -> str:
    lines: list[str] = []

    lines.append(f"# {cluster.identifier}: {cluster.crashes[0].message}")
    lines.append("")
    lines.append(f"**Severity:** {analysis.severity.upper()} · **Occurrences:** {cluster.count}")
    lines.append("")

    if analysis.failed:
        lines.append("## Analysis unavailable")
        lines.append("")
        lines.append(f"The model call failed: {analysis.error}")
        lines.append("")
    else:
        lines.append("## Root cause hypothesis")
        lines.append("")
        lines.append(analysis.root_cause or "No hypothesis returned.")
        lines.append("")

        lines.append("## Suspect commit")
        lines.append("")
        if analysis.suspect_commit:
            lines.append(f"- `{analysis.suspect_commit}` — {analysis.suspect_reason}")
        else:
            lines.append("No specific commit was identified as the cause.")
        lines.append("")

        lines.append("## Suggested next steps")
        lines.append("")
        for index, step in enumerate(analysis.next_steps, start=1):
            lines.append(f"{index}. {step}")
        lines.append("")

    frame = cluster.crashes[0].frames[0]
    lines.append("## Crash location")
    lines.append("")
    lines.append(f"`{frame.file}:{frame.line}`")
    lines.append("")

    lines.append("## Source context")
    lines.append("")
    if context.found:
        lines.append("```")
        for offset, line_text in enumerate(context.lines):
            line_number = context.start_line + offset
            marker = ">>" if line_number == frame.line else "  "
            lines.append(f"{marker} {line_number}: {line_text}")
        lines.append("```")
    else:
        lines.append("Source file could not be resolved.")
    lines.append("")

    lines.append("## Recent history on this line")
    lines.append("")
    if history.blame:
        for entry in history.blame:
            lines.append(f"- `{entry.short_sha}` {entry.author}: {entry.summary}")
    else:
        lines.append("No git history was available.")
    lines.append("")

    lines.append("## Crashes in this cluster")
    lines.append("")
    for identifier in cluster.crash_identifiers():
        lines.append(f"- `{identifier}`")
    lines.append("")

    return "\n".join(lines)


def write_reports(clusters_with_evidence, output_path: Path) -> Path:
    output_path.mkdir(parents=True, exist_ok=True)

    index_lines = ["# Crash triage index", ""]

    for cluster, context, history, analysis in clusters_with_evidence:
        filename = f"{cluster.identifier}.md"
        report_path = output_path / filename
        report_path.write_text(
            render_cluster_report(cluster, context, history, analysis),
            encoding="utf-8",
        )

        index_lines.append(
            f"- [{cluster.identifier}]({filename}) — "
            f"{analysis.severity.upper()}, {cluster.count} crashes"
        )

    index_path = output_path / "INDEX.md"
    index_path.write_text("\n".join(index_lines), encoding="utf-8")

    return index_path