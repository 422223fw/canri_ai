# Canri AI

Canri AI is a local, multi-brain Python assistant. It routes each request to
specialist components for understanding, code, mathematics, stories, facts,
memory, media, security, quality control, and final response formatting.

The project uses a shared runtime contract, isolated chat memory, indexed
local knowledge, targeted quality retries, cross-brain neural integration,
a request-scoped cognitive workspace, and atomic JSON storage. Normal
requests have no thinking deadline. The release version is reported by
`main_ai_canri/Main_brain.py` and is currently `1.1.4-alpha`.

## Requirements

- Python 3.10 or newer.
- Tk support for the desktop interface. It is included in standard Windows
  Python installations.
- Internet access is optional. It is needed only by enabled knowledge scanners
  and external-source refreshes.
- Git LFS is required when cloning or pushing the large data files tracked by
  `.gitattributes`.

The core assistant uses the Python standard library. Media features report a
clear limitation when a required local or external engine is unavailable.

## Run

From the project root:

```powershell
python .\main_ai_canri\main.py
```

The application starts the desktop chat interface and background knowledge
collectors. Chats are stored separately by session and restored on the next
launch. The sidebar can create, rename, delete, or clear chats; deleting a
chat also removes its isolated conversation memory.

To push committed project changes with the included helper:

```powershell
powershell -ExecutionPolicy Bypass -File .\push_canri.ps1
```

## Architecture

- `main.py`: application startup, request budget, brain registration, and GUI.
- `Manager_brain.py`: domain routing, execution phases, and targeted retries.
- `Cognitive_workspace.py`: one internal request ledger for the user goal,
  exact requirements, evidence, conflicts, candidate ranking, and correction
  packets. It scores verified coverage instead of answer length.
- `Nervous_system_brain.py`: internal requirement state, candidate ranking,
  and correction routing across specialist brains. It never writes the final
  user-facing answer.
- `Understanding_brain.py`: whole-request intent, entities, requirements, and
  sentence graph.
- `Data_context.py`: bounded retrieval from dictionaries, memory, scanners,
  and local knowledge indexes.
- `Brain_runtime.py`: uniform result contract, timeouts, safe errors, request
  IDs, and runtime telemetry.
- `Brain_storage.py`: resilient reads and atomic JSON writes.
- Specialist brains: code, math, science, history, geography, technology,
  story, character, world, image, movie, vision, voice, emotion, and others.
- Movie_brain.py and movie_engine/: full movie preproduction and render
  orchestration. The pipeline turns Creative, Story, Character, World, Image,
  Voice, Technology, research, scanner, dictionary, and memory context into a
  duration-locked screenplay, scene timeline, shot list, continuity ledger,
  asset catalog, sound/VFX plan, budget, schedule, and render manifest. Movie
  duration is capped at five hours.
- `Quality_Control_brain.py`: requirement-by-requirement acceptance checks.
- `Answer_Enrichment_brain.py`: prepares useful explanations, correction
  summaries, verification details, and run instructions when the user's output
  contract permits them. Strict output requests always disable these additions.
- `Response_brain.py`: clean final user output without internal reports.

`Code_brain.py` uses a multidimensional quality score. Single-file Python code
is scored for syntax, request coverage, implementation completeness, runnable
entry point, safety, and maintainability. Multi-file projects also score
architecture and preservation of existing files. A high total cannot hide a
blocking syntax error or a missing explicit requirement.

Quality failures are sent back to the responsible specialist with the exact
missing requirement. Canri can retry a specialist up to 20 times. If no
candidate reaches every advisory quality check, `Response_brain` still returns
the strongest usable result while keeping diagnostics in Thinking details.
Passed requirements are carried into later attempts so a correction should
not remove behavior that already worked.

## Data

- `main_ai_canri/data/`: brain-specific data, scanner queues, indexes,
  statistics, chat storage, and release criteria.
- `main_ai_canri/UnderstandingDk/data/`: dictionary, grammar, and connection
  data used by understanding and spelling.
- Large append-only knowledge databases use JSONL. Search code retrieves
  bounded relevant records instead of loading an entire database per request.
- `Nervous_system_profiles.json` configures domain owners, internal-only
  brains, candidate fields, and the correction-cycle limit.
- Runtime-created data is written atomically where replacement is supported.

Do not edit a large JSON file while Canri or a scanner is writing to it.

## Verification

Run these commands from the project root:

```powershell
python .\tools\validate_canri_project.py
python .\tools\check_brain_runtime.py
python .\tools\check_canri_regression.py
python .\tools\check_canri_release.py
python .\Canri_Tests\smoke_latest.py
python .\Canri_Tests\smoke_movie_brain.py
```

`check_canri_release.py` enforces the required 1.0.0 gates in
`main_ai_canri/data/Release_criteria.json`. A release is allowed only when at
least 100 checks run, at least 95 percent pass, and no critical invariant
fails.

Use the slower complete JSONL validation when preparing or repairing a data
archive:

```powershell
python .\tools\validate_canri_project.py --full-jsonl
```

## Photorealistic Movie Rendering

The local animatic is a timing storyboard, not a filmed-looking movie. Canri
can render the exported shot plan through Runway Gen-4.5 and then assemble the
downloaded shots into one local MP4 with FFmpeg.

```powershell
python -m pip install -r .\main_ai_canri\requirements-movie.txt
setx RUNWAYML_API_SECRET "YOUR_RUNWAY_KEY"
```

Restart the terminal after `setx`. Never put the key in source code, JSON, a
commit, or a chat message. Preview the calculated cost without making a paid
API call:

```powershell
python .\main_ai_canri\render_movie_runway.py ".\main_ai_canri\generated_movies\the_last_signal_9e79c057\movie_project.json" --max-cost-usd 25
```

After adding API credits and reviewing the estimate, authorize generation:

```powershell
python .\main_ai_canri\render_movie_runway.py ".\main_ai_canri\generated_movies\the_last_signal_9e79c057\movie_project.json" --max-cost-usd 25 --execute
```

In the desktop app, open `Settings` to configure the movie provider, model, budget,
and the `Allow paid movie rendering` switch. The switch is off by default, so
creating a movie package does not start a paid render accidentally. An API key
entered in the dialog is used only by the current Canri process and is never
written to `Movie_settings.json`; use `setx RUNWAYML_API_SECRET "YOUR_RUNWAY_KEY"`
when it should remain available after restarting Canri.

The renderer checkpoints every downloaded clip, resumes completed work after
failure, and refuses to begin when the estimated base cost exceeds the limit.
Retries can increase the final provider charge.

## Project Agent

Open `Settings`, select one Agent mode, and choose the exact project directory:

- `No Agent` keeps Canri in chat-only mode.
- `Agent - Autonomous` may apply generated files and run allowed development tools.
- `Agent - Restricted` uses a smaller terminal allowlist.
- `Agent - Ask Before Changes` reads project context but asks before every write or command.

The Agent indexes related files together and passes a bounded set of relevant source
files to the specialist brains. It creates a backup before overwriting an existing
file and records an audit entry locally. Approval mode returns commands such as
`/agent approve 12ab34cd56ef` or `/agent reject 12ab34cd56ef` in the chat.

Direct Agent commands are also available:

````text
/agent read path/to/file.py
/agent search ContactService
/agent run python -m pytest -q
/agent write path/to/file.py
```python
print("replacement file content")
```
````

Even Autonomous mode cannot leave the selected workspace, edit `.git`, invoke a
shell through Canri's command interface, or run blocked destructive/system operations.
However, project programs launched by the Agent receive the current Windows account's
normal permissions; Agent mode is not an operating-system sandbox. Use Autonomous only
for trusted projects. Local machine paths, pending approvals, and Agent audit records
are excluded from Git.

## Current Limits

- Canri is a deterministic local assistant architecture, not a general-purpose
  trained language model or AGI.
- Answer breadth depends on the installed local dictionaries, recipes, and
  collected knowledge.
- Current facts require refreshed sources; local records can become outdated.
- Vision and voice depth depends on available local engines and file formats.
- Image fallback output is programmatic and is not equivalent to a hosted
  photorealistic image model.
- Movie projects are complete provider-neutral production packages. A real
  photorealistic final master requires `RUNWAYML_API_SECRET` or another
  configured `movie_video_backend`, licensed references, provider credits,
  and sufficient remote render capacity. An animatic is generated only when
  explicitly requested and is never reported as the final movie.
- Normal requests have no thinking-time deadline. An optional emergency
  watchdog can be enabled with `CANRI_BRAIN_WATCHDOG_SECONDS=300` if a local
  deployment needs protection from a permanently stuck brain.

## Troubleshooting

- **GUI does not open:** verify Tk with `python -m tkinter`.
- **JSON decode error:** stop active scanners, run
  `python .\tools\validate_canri_project.py`, then restore the affected file
  from its backup if the failure persists.
- **Slow request:** inspect `main_ai_canri/data/Brain_runtime_statistics.json`
  for per-brain latency. Normal thinking is unlimited unless the optional
  watchdog environment variable is set.
- **Knowledge is not updating:** inspect the matching `*_scan_statistics.json`
  and `*_scan_queue.json` files and confirm network access.
- **Git LFS filter failed:** reinstall Git LFS, run `git lfs install`, restart
  the terminal, and retry the push helper.
- **Chat is missing:** inspect `Canri_chats.json` and its backup in
  `main_ai_canri/data/` before making manual changes.
