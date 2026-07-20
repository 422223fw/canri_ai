# Canri AI

Canri AI is a local, multi-brain Python assistant. It routes each request to
specialist components for understanding, code, mathematics, stories, facts,
memory, media, security, quality control, and final response formatting.

The project uses a bounded runtime contract, isolated chat memory, indexed
local knowledge, targeted quality retries, and atomic JSON storage. The
release version is reported by `main_ai_canri/Main_brain.py`.

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

The application starts the desktop chat interface and bounded background
knowledge collectors. Chats are stored separately by session and restored on
the next launch.

To push committed project changes with the included helper:

```powershell
powershell -ExecutionPolicy Bypass -File .\push_canri.ps1
```

## Architecture

- `main.py`: application startup, request budget, brain registration, and GUI.
- `Manager_brain.py`: domain routing, execution phases, and targeted retries.
- `Understanding_brain.py`: whole-request intent, entities, requirements, and
  sentence graph.
- `Data_context.py`: bounded retrieval from dictionaries, memory, scanners,
  and local knowledge indexes.
- `Brain_runtime.py`: uniform result contract, timeouts, safe errors, request
  IDs, and runtime telemetry.
- `Brain_storage.py`: resilient reads and atomic JSON writes.
- Specialist brains: code, math, science, history, geography, technology,
  story, character, world, image, vision, voice, emotion, and others.
- `Quality_Control_brain.py`: requirement-by-requirement acceptance checks.
- `Response_brain.py`: clean final user output without internal reports.

## Data

- `main_ai_canri/data/`: brain-specific data, scanner queues, indexes,
  statistics, chat storage, and release criteria.
- `main_ai_canri/UnderstandingDk/data/`: dictionary, grammar, and connection
  data used by understanding and spelling.
- Large append-only knowledge databases use JSONL. Search code retrieves
  bounded relevant records instead of loading an entire database per request.
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

## Current Limits

- Canri is a deterministic local assistant architecture, not a general-purpose
  trained language model or AGI.
- Answer breadth depends on the installed local dictionaries, recipes, and
  collected knowledge.
- Current facts require refreshed sources; local records can become outdated.
- Vision and voice depth depends on available local engines and file formats.
- Image fallback output is programmatic and is not equivalent to a hosted
  photorealistic image model.
- Normal requests have no thinking-time deadline. An optional emergency
  watchdog can be enabled with `CANRI_BRAIN_WATCHDOG_SECONDS=300` if a local
  deployment needs protection from a permanently stuck brain.

## Troubleshooting

- **GUI does not open:** verify Tk with `python -m tkinter`.
- **JSON decode error:** stop active scanners, run
  `python .\tools\validate_canri_project.py`, then restore the affected file
  from its backup if the failure persists.
- **Slow request:** inspect `main_ai_canri/data/Brain_runtime_statistics.json`
  for timeouts and per-brain latency.
- **Knowledge is not updating:** inspect the matching `*_scan_statistics.json`
  and `*_scan_queue.json` files and confirm network access.
- **Git LFS filter failed:** reinstall Git LFS, run `git lfs install`, restart
  the terminal, and retry the push helper.
- **Chat is missing:** inspect `Canri_chats.json` and its backup in
  `main_ai_canri/data/` before making manual changes.
