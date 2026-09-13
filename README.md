# crashtriage

A CLI tool that reads a crash log, finds the actual source code and git history for the file that crashed, and asks Gemini for a plain-English root cause. Given several crash logs at once, it groups the ones that look like the same bug first, so you get one report per real issue instead of one per crash.

```
crashtriage --repo ../game --crashes ./crashes --out reports
```

## Why I built this

This is my second GenAI portfolio project, and it's different from the first one, which was an AI changelog generator. That one summarizes: it takes git history and compresses it. This one retrieves and reasons: it starts from a crash, goes and finds the evidence that explains it, and only then produces an answer.

The actual problem is one every studio has. A build goes out, crash reports come back, and someone has to go through them one by one: open the file, find the function, run git blame, work out whether anything changed there recently, and decide how bad it is. Most of that list is usually the same handful of bugs reported repeatedly, but you can't tell which until you've read through all of them.

This automates the mechanical part. It doesn't fix bugs or replace a debugger. It turns a pile of crash logs into a handful of reports, each already carrying the code, the history, and a first hypothesis.

## How it works

1. **Parse** the crash log for stack frames (`file:line`, plus the function name where available) and the crash message.
2. **Cluster** crashes that look like the same underlying bug, based on the crash message and the top few stack frames, before anything gets sent to the model.
3. **Resolve source.** Crash logs carry build-machine paths like `D:\\build\\Source\\Game\\EnemySpawner.cpp`. The tool indexes the repo with `git ls-files` and matches by filename, then pulls the lines around the crash.
4. **Pull git history.** `git blame` on the crashing line, so the report can name the exact commit that touched it, not just a guess.
5. **Ask Gemini** for a root cause, a severity estimate, a suspect commit, and concrete next steps, giving it the numbered source with the crashing line explicitly marked so it doesn't have to guess which line actually failed.
6. **Write Markdown**, one report per cluster plus an index.

## Setup

Python 3.11+, git on PATH.

```bash
git clone <this repo> \&\& cd crashtriage
python -m venv .venv
.venv\\Scripts\\activate      # windows
source .venv/bin/activate   # mac/linux
pip install -e .
```

Get a free Gemini key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey), no card needed:

```bash
export GEMINI\_API\_KEY=AIza...          # mac/linux
$env:GEMINI\_API\_KEY = "AIza..."        # windows powershell
```

## Usage

```bash
crashtriage --repo ../game --crashes ./crashes --out reports
```

* `--repo`: the source repository to pull code and history from
* `--crashes`: a single crash log file, or a directory of them
* `--out`: where to write the generated reports, defaults to `triage-reports`

Logs with no recognisable stack trace are skipped with a warning rather than failing the whole run.

## Example

Five real crash logs, three of them the same bug, one a near-variant, one unrelated:

```
$ crashtriage --repo ../demo-game --crashes ../demo-crashes --out reports
parsed 6 crash logs, 5 had a usable trace
grouped into 2 clusters
  cluster-001: 1 crashes, severity low
  cluster-002: 4 crashes, severity high
wrote 2 report(s) to reports
index: reports/INDEX.md
```

`reports/cluster-002.md`:

```markdown
# cluster-002: Fatal error: Access violation reading address 0x00000001

\*\*Severity:\*\* HIGH · \*\*Occurrences:\*\* 4

## Root cause hypothesis

An out-of-bounds array access or uninitialized array read occurs when indexing
into WaveTable with WaveIndex. Bounds validation is missing before accessing
WaveTable\[WaveIndex].

## Suspect commit

- `b516564b`: Commit b516564b modified line 3 to calculate WaveSize using
  WaveTable\[WaveIndex] without validating that WaveIndex is within bounds.

## Suggested next steps

1. Add a bounds check against WaveTable.Num() before indexing WaveTable\[WaveIndex].
2. Verify where WaveIndex is calculated prior to calling SpawnWave.

## Source context

    1: void AEnemySpawner::SpawnWave(int32 WaveIndex)
    2: {
 >> 3:     const int32 WaveSize = WaveTable\[WaveIndex].Count \* DifficultyScale;
    4:
    5:     for (int32 Index = 0; Index < WaveSize; ++Index)

## Recent history on this line

- `b516564b` Oleksandr Pryimak: scale wave size by difficulty multiplier
```

Four separate crash logs, all reporting the same underlying bug, collapsed into one report pointing at the exact commit that caused it.

## Clustering, briefly

Each crash gets a key from its message and its top stack frames. Identical keys go into the same cluster directly. Everything else is compared with `difflib.SequenceMatcher` against existing cluster keys, so near-identical traces (same bug, slightly different line, different fault address) still group together instead of each getting filed separately.

## What I'd add next

* More crash formats. Right now it recognises one style of stack trace; a real version needs configurable patterns for Unreal, .NET, gdb, and whatever else shows up.
* Claude as an alternate provider, matching my changelog tool.
* A `--dry-run` mode to preview the prompt without spending an API call.
* A proper config file instead of only CLI flags.

## Known limitations

* Source context extraction is a fixed window around the crash line, not a real function-boundary parser.
* Only Gemini is supported right now.
* If the crash log's line number doesn't match what's actually in your checked-out code (different build, different revision), the tool will confidently look at the wrong line. It has no way to detect this on its own.
* A root cause from a language model is a hypothesis, not a verified diagnosis. Treat every report as a starting point, not an answer.

