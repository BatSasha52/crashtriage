import os
from pathlib import Path

from crashtriage.parsing import CrashLogParser
from crashtriage.clustering import cluster_crashes
from crashtriage.source import SourceResolver
from crashtriage.history import HistoryProvider, FileHistory
from crashtriage.llm import build_prompt, call_gemini
from crashtriage.report import write_reports

parser = CrashLogParser()
reports = parser.parse_path(Path(r"..\demo-crashes"))
usable = [r for r in reports if r.frames]
clusters = cluster_crashes(usable)

resolver = SourceResolver(Path(r"..\demo-game"))
provider = HistoryProvider(Path(r"..\demo-game"))

evidence = []
for cluster in clusters:
    frame = cluster.crashes[0].frames[0]
    context = resolver.context_for(frame.file, frame.line)

    if context.found:
        history = provider.history_for(context.resolved_path, frame.line)
    else:
        history = FileHistory(path="unknown")

    prompt = build_prompt(cluster, context, history.blame)
    analysis = call_gemini(os.environ["GEMINI_API_KEY"], prompt)

    evidence.append((cluster, context, history, analysis))
    print(f"analysed {cluster.identifier}: {analysis.severity}")

index_path = write_reports(evidence, Path("reports"))
print("wrote index to", index_path)