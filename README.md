# Canri AI

Canri AI is a local, multi-brain Python assistant. It routes each request to
specialist components for understanding, code, mathematics, stories, facts,
memory, media, security, quality control, and final response formatting.

The project uses a shared runtime contract, isolated chat memory, indexed
local knowledge, targeted quality retries, cross-brain neural integration,
a request-scoped cognitive workspace, and atomic JSON storage. Normal
requests have no thinking deadline. The release version is reported by
`main_ai_canri/data/Canri_self_profile.json` and is currently `1.2.0`.

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
  sentence graph. Domain selection is discovered from installed brains,
  package manifests, dictionary relations, and indexed evidence; duplicate
  keyword-to-brain tables are not used by the active routing path.
- `Semantic_router.py`: builds cached semantic profiles from the brains and
  their declared data instead of maintaining another domain hint dictionary.
- `domain_packages/`: active packages for code, science, technology,
  creativity, math, and user understanding. Each package keeps the established
  root brain intact, adds a manifest and bounded runtime context, and defines
  specialist handoffs and acceptance checks. The code package also contains a
  conservative editor for existing Agent projects.
- `Data_context.py`: bounded retrieval from dictionaries, memory, scanners,
  and local knowledge indexes.
- `Brain_runtime.py`: uniform result contract, safe errors, request IDs,
  runtime telemetry, per-brain UTF-8 information-volume accounting, and an
  optional emergency watchdog. Ordinary requests have no default thinking
  deadline.
- `Brain_storage.py`: resilient reads and atomic JSON writes.
- `Canri_self_profile.json`: versioned self-description of Canri's purpose,
  brains, capabilities, workflows, limits, and user-facing features. It is
  indexed by `Data_context.py`, while `Main_brain.py` and `Response_brain.py`
  use it as the canonical source for release and capability information.
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
- `Local_LLM_brain.py`: on-device advisory generation through CANRI's native
  model, a configured GGUF model, or local Ollama. It uses no cloud API and
  cannot execute its own output.
- `LLM_bridge_brain.py`: builds a bounded prompt from Understanding, isolated
  conversation memory, retrieved evidence, quality corrections, and specialist
  reports. Specialists remain authoritative. Native model text can become a
  general-conversation answer only after the sealed automated gate and manual
  review both pass.

`Code_brain.py` uses a multidimensional quality score. Single-file Python code
is scored for syntax, request coverage, implementation completeness, runnable
entry point, safety, and maintainability. Multi-file projects also score
architecture and preservation of existing files. A high total cannot hide a
blocking syntax error or a missing explicit requirement.

Code generation and quality control share
`data/Code_capability_ontology.json` and `data/Code_program_specs.json` through
`domain_packages/code/capabilities.py` and `domain_packages/code/program_specs.py`.
This keeps feature detection, program classification, generation, and review
on one request-derived interpretation instead of separate keyword tables.

Quality failures are sent back to the responsible specialist with the exact
missing requirement. Canri can retry a specialist up to 20 times. If no
candidate reaches every advisory quality check, `Response_brain` still returns
the strongest usable result while keeping diagnostics in Thinking details.
Passed requirements are carried into later attempts so a correction should
not remove behavior that already worked.

## Optional Local Language Model

The deterministic brains can route, retrieve, validate, and generate the
program types implemented by the project, but they are not a replacement for
a trained general-purpose language model. For request-specific conversation,
creative writing, and unfamiliar software architectures, Canri can use a
model that runs locally without a cloud API.

The current native v4 model has 9,028,800 parameters, 10 attention heads, and
a 500-token context window. It was expanded from v3 by weight transfer and
received a focused 1,500-step adaptation pass. It is connected in `advisory`
mode, but its sealed report is still `experimental_not_ready` (loss 3.112334,
generation score 60, semantic pass rate 0%). CANRI therefore records its
suggestion for collaboration and telemetry but does not expose it as the final
answer. This prevents an undertrained model from replacing working specialist
results.

Edit `main_ai_canri/data/Local_model_settings.json` to choose another backend:

1. Install `llama-cpp-python`, set `model_path` to a local GGUF file, and set
   `backend` to `llama_cpp`.
2. Install Ollama locally, download a model with Ollama, set `ollama_model` to
   its installed name, and set `backend` to `ollama`.
3. Keep `integration_mode` set to `advisory` until the selected model passes
   its quality review.

`timeout_seconds: 0` means no generation deadline. Prompt and output sizes are
still bounded to protect memory and prevent an accidental multi-gigabyte
response. Model files are not bundled with this repository. Their licenses,
RAM requirements, quality, and disk size vary. Enabling a small local model
does not by itself make Canri equal to Claude or another frontier model.

Every completed response includes an information-memory summary. The button
under the answer shows the total, LFM, and LLM volume; opening it shows every
brain's reads, writes, calls, and transfer edges. `Memory statistics` in the
header displays aggregate totals and a per-request graph. These values measure
serialized UTF-8 context and reports, not operating-system RAM.

`Planner_brain.py` builds executable steps from the current structured request
contract. Stored templates are used only as quality and risk references; they
do not decide the request domain or replace the user's requirements.

## Data

- `main_ai_canri/data/`: brain-specific data, scanner queues, indexes,
  statistics, chat storage, and release criteria.
- `main_ai_canri/UnderstandingDk/data/`: dictionary, grammar, and connection
  data used by understanding and spelling.
- Large append-only knowledge databases use JSONL. Search code retrieves
  bounded relevant records instead of loading an entire database per request.
- `Nervous_system_profiles.json` configures domain owners, internal-only
  brains, candidate fields, and the correction-cycle limit.
- `Emotion_language_rules.json` keeps emotion-language rules in data, while
  `Emotion_brain.py` uses direct text plus `Understanding_brain` definitions;
  broad dictionary associations are not treated as direct emotional evidence.
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

When Agent mode is enabled, an explicit `Use Agent mode ...` request stays in
the Agent workflow on continuation turns. Canri loads the active chat's Agent
artifact and current workspace files, obtains a creative enhancement pass when
appropriate, validates the generated project with `Quality_Control_brain`, and
only then applies the verified files. If Agent mode is disabled, the same
explicit request returns a configuration message instead of silently running.

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

## Native Model From Scratch

`main_ai_canri/domain_packages/local_llm/` contains an experimental causal
Transformer that starts with random weights. It does not download or use a
pre-trained model. The package includes a hybrid word/Unicode tokenizer,
streaming access to every JSON, JSONL, and SQLite source in CANRI's data
directory, resumable checkpointing, and local inference:

```powershell
python -m main_ai_canri.domain_packages.local_llm.train `
  --rebuild-tokenizer --sampling-mode balanced --max-steps 200
```

PyTorch is optional and must be installed separately for training. Data is read
incrementally and is not copied into a second large corpus. This model is a
research foundation, not a Claude-equivalent model. The existing
`Local_LLM_brain` can use it with `backend: "canri_native"` after a checkpoint
exists; Understanding, specialist brains, Quality Control, and Response remain
responsible for grounding and validating its output.

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
