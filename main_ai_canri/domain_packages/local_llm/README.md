# CANRI Native LLM

This package contains CANRI's experimental causal Transformer. The original
model and the v2 model were initialized and trained locally; no downloaded
pre-trained model is used. Version 2 expands the original architecture through
weight transfer while preserving every inherited tokenizer id.

The current backend is connected in advisory mode. A checkpoint existing on
disk is not enough to make it a reliable assistant: held-out loss, generation
review, and manual approval must all pass before model text can become a
user-facing answer.

## Current v4 architecture and integration

- Vocabulary: 8,448 tokens
- Context: 500 tokens
- Width: 320
- Transformer layers: 5
- Attention heads: 10
- Parameters: 9,028,800
- Inference checkpoint: `checkpoints/canri_native_v4_inference.pt`

V4 preserves the v3 tokenizer and transfers all compatible weights. Its
position embedding is extended from 256 to 500 positions; inherited positions
are copied and new positions are initialized for adaptation. A focused 1,500
step instruction pass followed the transfer.

`LLM_bridge_brain` gives the model only context that fits its real token
budget. It prioritizes the exact request, request contract, Quality corrections,
specialist reports, relevant isolated memory, Understanding, and retrieved
knowledge. The bridge never replaces a specialist or executes generated text.

The sealed v4 evaluation currently reports loss 3.112334, generation score 60,
semantic pass rate 0%, and code pass rate 0%. It therefore remains an internal
advisor. Once both the sealed automated gate and manual review pass, the same
bridge can allow a reviewed candidate to answer general conversation.

## Version 2 architecture

- Vocabulary: 8,448 tokens
- Context: 256 tokens
- Width: 224
- Transformer layers: 5
- Attention heads: 7
- Parameters: 4,975,264
- Head width: 32, matching v1 (`192 / 6 == 224 / 7`)

The full training checkpoint also contains AdamW state and is therefore much
larger than the model weights alone. Use `export.py` for an inference-only
artifact.

## Training data policy

Training streams approved files under `main_ai_canri/data`; it does not load
the entire data directory into memory. The allowlist and exclusions live in
`training_data_policy.json`. Trusted knowledge, code, technical dictionaries,
mathematics, geography, history, product records, and curated instruction
seeds are eligible. Chats, queues, indexes, statistics, settings, audit logs,
and unverified learned memories are excluded as training targets.

JSON and JSONL are read incrementally. SQLite is opened read-only and traversed
in batches. Balanced raw training samples every approved source in round-robin
order so one large JSONL database cannot hide smaller sources.

Instruction tuning derives request/answer pairs from trusted records. It uses
a deterministic train/validation partition and computes loss only on assistant
completion tokens. Prompt and padding labels are masked. Batches are trimmed
dynamically to avoid computing over unused padding.

`build_quality_corpus.py` creates deterministic, inspectable JSONL shards from
trusted structured records and reviewed behavior seeds. It excludes previous
CANRI chats, learned memory, queues, model output, and every exact prompt in
`evaluation/sealed_holdout_v2.json`. The corpus manifest records hashes and
the leakage checks used when it was built.

## Install training support

PyTorch is optional. Install a matching build before training:

```powershell
python -m pip install --no-cache-dir numpy
python -m pip install --no-cache-dir torch `
  --index-url https://download.pytorch.org/whl/cpu
```

## Transfer v1 weights into v2

The transfer operation does not overwrite v1. It expands the tokenizer,
copies embedding and positional overlaps, copies Q/K/V attention blocks
separately, transfers compatible feed-forward and normalization weights, and
bootstraps the fifth layer from the fourth layer's compatible region.

```powershell
python -m main_ai_canri.domain_packages.local_llm.transfer
```

The report is written to `weight_transfer_report_v2.json`. The resulting v2
checkpoint starts its own step counter at zero while retaining v1's source step
count in its lineage.

## Train v2 on approved CANRI data

Run a balanced coverage pass across every approved source:

```powershell
python -m main_ai_canri.domain_packages.local_llm.train `
  --resume `
  --checkpoint .\main_ai_canri\domain_packages\local_llm\checkpoints\canri_native_v2.pt `
  --tokenizer .\main_ai_canri\domain_packages\local_llm\data\canri_tokenizer_v2.json `
  --objective language_model `
  --sampling-mode balanced `
  --samples-per-source 64 `
  --epochs 1
```

Then instruction-tune the same checkpoint:

```powershell
python -m main_ai_canri.domain_packages.local_llm.train `
  --resume `
  --checkpoint .\main_ai_canri\domain_packages\local_llm\checkpoints\canri_native_v2.pt `
  --tokenizer .\main_ai_canri\domain_packages\local_llm\data\canri_tokenizer_v2.json `
  --objective instruction `
  --instruction-min-quality 80 `
  --instruction-curated-repeats 8 `
  --max-steps 1000
```

After evaluation, focus a later pass on sources whose held-out loss remains
high. The source set is read from the report rather than hard-coded:

```powershell
python -m main_ai_canri.domain_packages.local_llm.train `
  --resume `
  --checkpoint .\main_ai_canri\domain_packages\local_llm\checkpoints\canri_native_v2.pt `
  --tokenizer .\main_ai_canri\domain_packages\local_llm\data\canri_tokenizer_v2.json `
  --objective instruction `
  --instruction-focus-status .\main_ai_canri\domain_packages\local_llm\training_status_v2.json `
  --instruction-focus-min-loss 1.5 `
  --max-steps 1000
```

## Evaluate and review

```powershell
python -m main_ai_canri.domain_packages.local_llm.evaluate `
  --checkpoint .\main_ai_canri\domain_packages\local_llm\checkpoints\canri_native_v2.pt `
  --tokenizer .\main_ai_canri\domain_packages\local_llm\data\canri_tokenizer_v2.json `
  --output .\main_ai_canri\domain_packages\local_llm\training_status_v2.json `
  --examples 512 `
  --maximum-validation-loss 1.5

python -m main_ai_canri.domain_packages.local_llm.review `
  --checkpoint .\main_ai_canri\domain_packages\local_llm\checkpoints\canri_native_v2.pt `
  --tokenizer .\main_ai_canri\domain_packages\local_llm\data\canri_tokenizer_v2.json `
  --output .\main_ai_canri\domain_packages\local_llm\generation_review_v2.json
```

The post-transfer sealed evaluator also generates answers, validates explicit
request signals, parses generated Python, and runs restricted pure-function
behavior checks. It never executes imports, attribute access, file operations,
or unrestricted generated code:

```powershell
python -m main_ai_canri.domain_packages.local_llm.sealed_evaluate `
  --checkpoint .\main_ai_canri\domain_packages\local_llm\checkpoints\canri_native_v2.pt `
  --tokenizer .\main_ai_canri\domain_packages\local_llm\data\canri_tokenizer_v2.json
```

`sealed_evaluation_v2.json` is the activation report used by
`Local_LLM_brain`. Readiness requires at least 20,000 v2 steps, sealed loss at
or below 1.5, generation score at or above 85, at least 90% semantic passes,
all code checks passing, corpus integrity, and explicit manual approval.

## Resumable training campaign

The campaign runner trains in atomic 250-step cycles, evaluates every 1,000
steps, exports current inference weights, and resumes from the AdamW state in
the full checkpoint. It reaches at least 20,000 steps and continues only while
the automated quality gate is still failing, up to the hard limit.

```powershell
python -m main_ai_canri.domain_packages.local_llm.campaign `
  --minimum-target-steps 20000 `
  --hard-limit-steps 40000 `
  --cycle-steps 250 `
  --evaluation-every 1000
```

Live state is written to `training_campaign_v2.json`; event history and full
subprocess output are written to `training_campaign_v2.jsonl` and
`training_campaign_v2.log`. To request a graceful stop after the active cycle:

```powershell
New-Item .\main_ai_canri\domain_packages\local_llm\training_campaign_v2.stop `
  -ItemType File -Force
```

Run the campaign command again to resume. A lock prevents two campaigns from
writing the same checkpoint simultaneously.

## Export for inference

```powershell
python -m main_ai_canri.domain_packages.local_llm.export
```

This creates `checkpoints/canri_native_v2_inference.pt` without optimizer
moments. `Local_model_settings.json` points to this artifact but keeps
`enabled` and `native_allow_experimental` false until quality gates pass.

## Realistic limits

A five-million-parameter model trained for several thousand CPU steps is an
engineering-valid local language model, but it is not comparable to modern
large assistants. Disk space does not replace high-quality tokens, compute,
or evaluation. Do not enable v2 while generation review is incoherent, even if
a single training batch reports loss below the requested threshold.

## Native v3: ten-head transfer campaign

`canri_native_v3.pt` expands v2 from seven 32-dimensional attention heads to
ten heads while preserving the same per-head width. The model has a width of
320, five Transformer layers, 8,950,720 parameters, and an 8,448-token
`hybrid_word_byte_v3` tokenizer. Weight transfer maps embeddings by exact token
identity and preserves compatible Transformer weights; the three added heads,
new hidden dimensions, and new byte-fallback tokens are then adapted by
instruction training. Inference constrains fallback bytes to complete valid
UTF-8 sequences and suppresses internal conversation markers until a minimum
answer has been generated.

The active v3 campaign uses focused code, instruction-following, conversation,
Hebrew, and mathematics sources until step 4,000. It then trains against the
complete approved corpus. Its state is stored in `training_campaign_v3.json`,
and its sealed release report is `sealed_evaluation_v3.json`.

The v3 activation gate remains deliberately strict: sealed loss must be at most 1.5,
generation score is at least 85, semantic pass rate is at least 90%, every code
case passes, and a human has approved generated samples. After those conditions
are met, activate it with:

```powershell
python -m main_ai_canri.domain_packages.local_llm.activate --approve
```

The activation command validates the sealed report again before atomically
enabling `canri_native` in `Local_model_settings.json`.
