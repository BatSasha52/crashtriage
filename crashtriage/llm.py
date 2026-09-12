from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field

SYSTEM_PROMPT = """You are a crash triage engineer on a game development team.
You read a stack trace, the source code around the crash, and git blame for that
code, then explain the likely root cause in plain English.

Rules:
- The source code below is numbered. The line marked with >> is the exact line
  that crashed. Lines without >> are shown only for context.
- Only name a suspect commit if that commit's blame entry is specifically on the
  >> line, or on a line the >> line clearly depends on (a variable it reads).
  Do not name a commit just because it is the oldest or the most recent one shown.
- If no commit in the blame data specifically touches the crashing line or a line
  it obviously depends on, leave suspect_commit as an empty string. That is a
  correct and useful answer, not a failure.
- Severity reflects real player impact: a crash on a common path is high or
  critical, a rare edge case is low or medium.

Respond with a single JSON object and nothing else, no markdown fences, matching this shape:
{
  "root_cause": "two to four sentences in plain English",
  "severity": "low | medium | high | critical",
  "suspect_commit": "short sha, or empty string if no line-level match",
  "suspect_reason": "one sentence, or empty string if suspect_commit is empty",
  "next_steps": ["concrete action", "concrete action"]
}"""


@dataclass
class TriageAnalysis:
    root_cause: str = ""
    severity: str = "unknown"
    suspect_commit: str = ""
    suspect_reason: str = ""
    next_steps: list[str] = field(default_factory=list)
    error: str = ""

    @property
    def failed(self) -> bool:
        return bool(self.error)


def build_prompt(cluster, context, blame_entries) -> str:
    frame = cluster.crashes[0].frames[0]

    numbered_lines = []
    for offset, line_text in enumerate(context.lines):
        line_number = context.start_line + offset
        marker = ">>" if line_number == frame.line else "  "
        numbered_lines.append(f"{marker} {line_number}: {line_text}")

    blame_lines = []
    for entry in blame_entries:
        is_crash_line = " (THIS IS THE CRASHING LINE)" if entry.line_number == frame.line else ""
        blame_lines.append(
            f"line {entry.line_number}: commit {entry.short_sha} by {entry.author} "
            f"\"{entry.summary}\"{is_crash_line}"
        )

    payload = {
        "crash_message": cluster.crashes[0].message,
        "crash_count_in_cluster": cluster.count,
        "crashing_file": frame.file,
        "crashing_line_number": frame.line,
        "numbered_source_code": numbered_lines if context.found else ["source not found"],
        "blame_per_line": blame_lines if blame_lines else ["no blame data available"],
    }

    return "Triage this crash:\n\n" + json.dumps(payload, indent=2)


def call_gemini(api_key: str, prompt: str) -> TriageAnalysis:
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent"

    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={"content-type": "application/json", "x-goog-api-key": api_key},
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        analysis = TriageAnalysis()
        analysis.error = f"HTTP {exc.code}: {exc.read().decode(errors='replace')[:300]}"
        return analysis

    text = raw["candidates"][0]["content"]["parts"][0]["text"]
    data = json.loads(text)

    return TriageAnalysis(
        root_cause=data.get("root_cause", ""),
        severity=data.get("severity", "unknown"),
        suspect_commit=data.get("suspect_commit", ""),
        suspect_reason=data.get("suspect_reason", ""),
        next_steps=data.get("next_steps", []),
    )