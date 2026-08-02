"""Curated instruction examples derived from CANRI's trusted local data.

Raw scanner data is useful for language-model pretraining, but it does not
teach the model to map a user request to a clean answer. This module derives
supervised-looking examples without trusting CANRI's previous low-quality chat
outputs as ground truth.
"""

from __future__ import annotations

import ast
import hashlib
import json
import random
import re
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Literal

from .dataset import DATA_ROOT
from .tokenizer import CanriTokenizer


IGNORE_INDEX = -100
INSTRUCTION_SPLIT_VERSION = "sha256_v1"
InstructionSplit = Literal["all", "train", "validation"]
PACKAGE_ROOT = Path(__file__).resolve().parent
QUALITY_SEED_BANK = PACKAGE_ROOT / "quality_sources" / "quality_seed_bank.json"
QUALITY_CORPUS_ROOT = PACKAGE_ROOT / "quality_corpus"


@dataclass(frozen=True)
class InstructionExample:
    user: str
    assistant: str
    source: str
    quality: float

    def formatted(self) -> str:
        return (
            "<|user|>\n"
            + self.user.strip()
            + "\n<|assistant|>\n"
            + self.assistant.strip()
            + "\n<|end|>\n"
        )


@dataclass(frozen=True)
class InstructionTrainingWindow:
    """A fixed context window with labels masked outside the assistant answer."""

    token_ids: tuple[int, ...]
    target_ids: tuple[int, ...]
    source: str


def _example_digest(example: InstructionExample) -> str:
    return hashlib.sha256(
        (example.user.casefold() + "\0" + example.assistant.casefold()).encode(
            "utf-8", errors="replace"
        )
    ).hexdigest()


def _belongs_to_split(
    digest: str,
    split: InstructionSplit,
    validation_fraction: float,
) -> bool:
    if split == "all":
        return True
    fraction = min(0.25, max(0.01, float(validation_fraction)))
    bucket = int(digest[:8], 16) / 0xFFFFFFFF
    is_validation = bucket < fraction
    return is_validation if split == "validation" else not is_validation


def _buffered_shuffle(
    values: Iterable[InstructionExample],
    *,
    buffer_size: int,
    seed: int,
) -> Iterator[InstructionExample]:
    size = max(1, int(buffer_size))
    if size <= 1:
        yield from values
        return
    randomizer = random.Random(int(seed))
    buffer: list[InstructionExample] = []
    for value in values:
        if len(buffer) < size:
            buffer.append(value)
            continue
        index = randomizer.randrange(len(buffer))
        yield buffer[index]
        buffer[index] = value
    randomizer.shuffle(buffer)
    yield from buffer


def _repair_mojibake(value: str) -> str:
    text = str(value or "")
    if not any(marker in text for marker in ("Ã", "Â", "â", "×")):
        return text
    try:
        repaired = text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text
    original_markers = sum(text.count(marker) for marker in ("Ã", "Â", "â", "×"))
    repaired_markers = sum(repaired.count(marker) for marker in ("Ã", "Â", "â", "×"))
    return repaired if repaired_markers < original_markers else text


def _clean_prose(value, limit: int = 1_600) -> str:
    text = _repair_mojibake(str(value or ""))
    text = re.sub(r"[\t\r ]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[: max(1, int(limit))].rstrip()


def _iter_jsonl(path: Path) -> Iterator[dict]:
    if not path.is_file():
        return
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                value = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(value, dict):
                yield value


def _knowledge_examples(data_root: Path) -> Iterator[InstructionExample]:
    files = (
        "Knowledge_database.jsonl",
        "general_scan_database.jsonl",
        "product_scan_database.jsonl",
        "code_scan_database.jsonl",
    )
    prompts = (
        "What is {title}? Give a clear factual answer.",
        "Explain {title} clearly and accurately.",
        "Give a concise, reliable overview of {title}.",
    )
    for file_name in files:
        path = data_root / file_name
        for index, record in enumerate(_iter_jsonl(path)):
            trust = float(record.get("source_trust_score", record.get("trust_score", 0)) or 0)
            title = _clean_prose(record.get("title"), 220)
            answer = _clean_prose(record.get("summary") or record.get("text"), 1_400)
            if trust < 70 or len(title) < 2 or len(answer) < 50:
                continue
            if answer.casefold().startswith("scholarly metadata for") and len(answer) < 140:
                continue
            source_name = _clean_prose(record.get("source_name"), 120)
            if source_name and source_name.casefold() not in answer.casefold():
                answer = f"{answer}\n\nSource: {source_name}."
            yield InstructionExample(
                user=prompts[index % len(prompts)].format(title=title),
                assistant=answer,
                source=file_name,
                quality=min(100.0, trust),
            )


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None


def _curated_seed_examples(data_root: Path) -> Iterator[InstructionExample]:
    """Load human-reviewed behavior examples without trusting old chat output."""

    payload = _load_json(data_root / "Local_llm_instruction_seeds.json")
    records = payload.get("examples", []) if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        return
    for item in records:
        if not isinstance(item, dict):
            continue
        user = _clean_prose(item.get("user"), 1_000)
        assistant = _repair_mojibake(str(item.get("assistant") or "")).strip()[:4_000]
        quality = float(item.get("quality", 0) or 0)
        if len(user) < 2 or len(assistant) < 2 or quality < 85:
            continue
        yield InstructionExample(
            user=user,
            assistant=assistant,
            source="Local_llm_instruction_seeds.json",
            quality=min(100.0, quality),
        )


def _quality_seed_bank_examples() -> Iterator[InstructionExample]:
    payload = _load_json(QUALITY_SEED_BANK)
    records = payload.get("examples", []) if isinstance(payload, dict) else []
    if not isinstance(records, list):
        return
    for item in records:
        if not isinstance(item, dict):
            continue
        user = _clean_prose(item.get("user"), 1_200)
        assistant = _repair_mojibake(str(item.get("assistant") or "")).strip()[:4_000]
        quality = float(item.get("quality", 0) or 0)
        if len(user) < 2 or len(assistant) < 2 or quality < 90:
            continue
        yield InstructionExample(
            user=user,
            assistant=assistant,
            source="quality_sources/quality_seed_bank.json",
            quality=min(100.0, quality),
        )


def _quality_corpus_examples() -> Iterator[InstructionExample]:
    if not QUALITY_CORPUS_ROOT.is_dir():
        return

    def from_path(path: Path) -> Iterator[InstructionExample]:
        for record in _iter_jsonl(path):
            user = _clean_prose(record.get("user"), 1_200)
            assistant = _repair_mojibake(
                str(record.get("assistant") or "")
            ).strip()[:4_000]
            quality = float(record.get("quality", 0) or 0)
            if len(user) < 2 or len(assistant) < 2 or quality < 85:
                continue
            yield InstructionExample(
                user=user,
                assistant=assistant,
                source=f"quality_corpus/{path.name}",
                quality=min(100.0, quality),
            )

    iterators = deque(
        iter(from_path(path))
        for path in sorted(QUALITY_CORPUS_ROOT.glob("*.jsonl"))
    )
    while iterators:
        iterator = iterators.popleft()
        try:
            yield next(iterator)
        except StopIteration:
            continue
        iterators.append(iterator)


def _training_repeats_for_source(source: str, curated_repeats: int) -> int:
    repeats = max(1, int(curated_repeats))
    if source in {
        "Local_llm_instruction_seeds.json",
        "quality_sources/quality_seed_bank.json",
    } or source.startswith("quality_corpus/conversation"):
        return repeats
    if source.startswith("quality_corpus/code_behavior"):
        return repeats
    if source.startswith("quality_corpus/task_following"):
        return max(2, repeats // 2)
    if source.startswith(("quality_corpus/code", "quality_corpus/math")):
        return max(2, repeats // 4)
    return 1


def _code_template_examples(data_root: Path) -> Iterator[InstructionExample]:
    payload = _load_json(data_root / "Code_library_templates.json")
    templates = payload.get("templates", {}) if isinstance(payload, dict) else {}
    if not isinstance(templates, dict):
        return
    for item in templates.values():
        if not isinstance(item, dict):
            continue
        qualified = _clean_prose(item.get("qualified_name"), 160)
        summary = _clean_prose(item.get("summary"), 900)
        import_statement = _clean_prose(item.get("import_statement"), 240)
        call_template = _clean_prose(item.get("call_template"), 400)
        source = item.get("source") if isinstance(item.get("source"), dict) else {}
        trust = float(source.get("trust_score", 0) or 0)
        if trust < 85 or not qualified or not summary or not call_template:
            continue
        code = "\n".join(part for part in (import_statement, call_template) if part)
        yield InstructionExample(
            user=f"Show how to call {qualified} in Python and explain what it does.",
            assistant=f"```python\n{code}\n```\n\n{summary}",
            source="Code_library_templates.json",
            quality=trust,
        )


def _valid_code_snippet(item: dict) -> bool:
    code = str(item.get("code") or "").strip()
    description = str(item.get("description") or "").casefold()
    lowered = code.casefold()
    rejected = (
        "production draft variant",
        "helper, production",
        "data = data or {}",
        "result = none",
        "todo",
        "not implemented",
        "placeholder",
    )
    if not (8 <= len(code) <= 4_000) or any(value in lowered or value in description for value in rejected):
        return False
    if str(item.get("language") or "").casefold() == "python":
        try:
            ast.parse(code)
        except SyntaxError:
            return False
    return True


def _code_snippet_examples(data_root: Path) -> Iterator[InstructionExample]:
    payload = _load_json(data_root / "code.json")
    if not isinstance(payload, list):
        return
    emitted = 0
    seen_code: set[str] = set()
    for item in payload:
        if not isinstance(item, dict) or not _valid_code_snippet(item):
            continue
        language = _clean_prose(item.get("language") or "code", 40)
        description = _clean_prose(
            item.get("description") or item.get("name") or item.get("category"),
            300,
        )
        code = str(item.get("code") or "").strip()
        if not description:
            continue
        fingerprint = hashlib.sha256(code.casefold().encode("utf-8", errors="replace")).hexdigest()
        if fingerprint in seen_code:
            continue
        seen_code.add(fingerprint)
        yield InstructionExample(
            user=f"Write a correct {language} example for this request: {description}",
            assistant=f"```{language}\n{code}\n```",
            source="code.json",
            quality=85.0,
        )
        emitted += 1
        if emitted >= 6_000:
            return


def _project_recipe_examples(data_root: Path) -> Iterator[InstructionExample]:
    payload = _load_json(data_root / "Code_project_recipes.json")
    if not isinstance(payload, dict):
        return
    for recipe in payload.values():
        if not isinstance(recipe, dict):
            continue
        score = float(recipe.get("quality_score", 0) or 0)
        title = _clean_prose(recipe.get("title"), 160)
        focus = _clean_prose(recipe.get("focus"), 100)
        components = [
            _clean_prose(item, 180)
            for item in recipe.get("components", [])
            if _clean_prose(item, 180)
        ]
        checks = [
            _clean_prose(item, 220)
            for item in recipe.get("acceptance_criteria", [])
            if _clean_prose(item, 220)
        ]
        if score < 75 or not title or not components:
            continue
        answer_parts = ["Implementation components:"]
        answer_parts.extend(f"- {item}" for item in components[:10])
        if checks:
            answer_parts.append("Acceptance checks:")
            answer_parts.extend(f"- {item}" for item in checks[:8])
        yield InstructionExample(
            user=f"Plan a reliable Python {title} focused on {focus or 'correctness'}.",
            assistant="\n".join(answer_parts),
            source="Code_project_recipes.json",
            quality=score,
        )


def _math_formula_examples(data_root: Path) -> Iterator[InstructionExample]:
    payload = _load_json(data_root / "Math_formulas.json")
    if not isinstance(payload, dict):
        return
    for item in payload.values():
        if not isinstance(item, dict):
            continue
        name = _clean_prose(item.get("name"), 120)
        formula = _clean_prose(item.get("formula"), 500)
        verification = _clean_prose(item.get("verification"), 300)
        if not name or not formula:
            continue
        answer = f"Formula: {formula}"
        if verification:
            answer += f"\nVerification: {verification}."
        yield InstructionExample(
            user=f"Explain the {name} formula and how to verify the result.",
            assistant=answer,
            source="Math_formulas.json",
            quality=92.0,
        )


def _translation_examples(data_root: Path) -> Iterator[InstructionExample]:
    payload = _load_json(data_root / "Translation_dictionary.json")
    if not isinstance(payload, dict):
        return
    emitted = 0
    for fallback_word, translations in payload.items():
        if not isinstance(translations, dict):
            continue
        english = _clean_prose(translations.get("en") or fallback_word, 100)
        hebrew = _clean_prose(translations.get("he"), 100)
        french = _clean_prose(translations.get("fr"), 100)
        if english and hebrew and english.casefold() != hebrew.casefold():
            yield InstructionExample(
                user=f"Translate {english!r} from English to Hebrew.",
                assistant=hebrew,
                source="Translation_dictionary.json",
                quality=96.0,
            )
            emitted += 1
        if english and french and english.casefold() != french.casefold():
            yield InstructionExample(
                user=f"Translate {english!r} from English to French.",
                assistant=french,
                source="Translation_dictionary.json",
                quality=94.0,
            )
            emitted += 1
        if emitted >= 12_000:
            return


def _lexical_relation_examples(data_root: Path) -> Iterator[InstructionExample]:
    for file_name, relation in (
        ("Synonyms.json", "synonyms"),
        ("Antonyms.json", "antonyms"),
    ):
        payload = _load_json(data_root / file_name)
        if not isinstance(payload, dict):
            continue
        emitted = 0
        for word, raw_values in payload.items():
            values = raw_values if isinstance(raw_values, list) else [raw_values]
            cleaned = [
                _clean_prose(item, 80)
                for item in values
                if _clean_prose(item, 80)
            ]
            term = _clean_prose(word, 100)
            if not term or not cleaned:
                continue
            yield InstructionExample(
                user=f"Give the {relation} of {term!r}.",
                assistant=", ".join(cleaned[:8]),
                source=file_name,
                quality=94.0,
            )
            emitted += 1
            if emitted >= 5_000:
                break


def _technical_vocabulary_examples(data_root: Path) -> Iterator[InstructionExample]:
    technical = _load_json(data_root / "Technical_terms.json")
    if isinstance(technical, dict):
        for term, item in technical.items():
            if not isinstance(item, dict):
                continue
            name = _clean_prose(term, 100)
            meaning = _clean_prose(item.get("meaning"), 700)
            field = _clean_prose(item.get("field"), 80)
            if name and meaning:
                answer = meaning + (f" Field: {field}." if field else "")
                yield InstructionExample(
                    user=f"Explain the technical term {name!r}.",
                    assistant=answer,
                    source="Technical_terms.json",
                    quality=95.0,
                )

    hardware = _load_json(data_root / "Hardware_dictionary.json")
    if isinstance(hardware, dict):
        for term, item in hardware.items():
            if not isinstance(item, dict):
                continue
            role = _clean_prose(item.get("role"), 800)
            specs = [
                _clean_prose(value, 100)
                for value in item.get("important_specs", [])
                if _clean_prose(value, 100)
            ]
            if role:
                answer = role
                if specs:
                    answer += " Important specifications: " + ", ".join(specs[:8]) + "."
                yield InstructionExample(
                    user=f"What is a {str(term).upper()} and which specifications matter?",
                    assistant=answer,
                    source="Hardware_dictionary.json",
                    quality=96.0,
                )

    units = _load_json(data_root / "Units_dictionary.json")
    if isinstance(units, dict):
        for symbol, item in units.items():
            if not isinstance(item, dict):
                continue
            name = _clean_prose(item.get("name"), 100)
            unit_type = _clean_prose(item.get("type"), 80)
            if name:
                yield InstructionExample(
                    user=f"What does the unit symbol {str(symbol)!r} mean?",
                    assistant=f"{symbol} means {name}. It is a unit of {unit_type or 'measurement'}.",
                    source="Units_dictionary.json",
                    quality=94.0,
                )


def _iter_nested_records(value, depth: int = 0) -> Iterator[dict]:
    if depth > 4:
        return
    if isinstance(value, dict):
        if any(key in value for key in ("title", "name", "word", "product")) and any(
            key in value for key in ("summary", "description", "definition", "text")
        ):
            yield value
        for child in value.values():
            yield from _iter_nested_records(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_nested_records(child, depth + 1)


def _structured_domain_examples(data_root: Path) -> Iterator[InstructionExample]:
    files = (
        "Company_products.json",
        "Geography_places.json",
        "Geography_concepts.json",
        "History_events.json",
        "History_figures.json",
        "Technology_terms.json",
        "Canri_self_profile.json",
    )
    for file_name in files:
        payload = _load_json(data_root / file_name)
        for item in _iter_nested_records(payload):
            title = _clean_prose(
                item.get("title") or item.get("name") or item.get("word") or item.get("product"),
                180,
            )
            answer = _clean_prose(
                item.get("summary")
                or item.get("description")
                or item.get("definition")
                or item.get("text"),
                1_200,
            )
            if title and len(answer) >= 30:
                yield InstructionExample(
                    user=f"Explain {title} clearly.",
                    assistant=answer,
                    source=file_name,
                    quality=85.0,
                )


def iter_instruction_examples(
    data_root: Path = DATA_ROOT,
    *,
    minimum_quality: float = 75.0,
    max_examples: int = 0,
    split: InstructionSplit = "all",
    validation_fraction: float = 0.05,
    max_examples_per_source: int = 0,
    include_sources: set[str] | None = None,
    include_package_quality: bool | None = None,
) -> Iterator[InstructionExample]:
    """Round-robin trusted domains with a deterministic train/validation split."""

    if split not in {"all", "train", "validation"}:
        raise ValueError("Instruction split must be 'all', 'train', or 'validation'.")

    root = Path(data_root)
    if include_package_quality is None:
        try:
            include_package_quality = root.resolve() == DATA_ROOT.resolve()
        except OSError:
            include_package_quality = False
    package_sources: tuple[Iterable[InstructionExample], ...] = ()
    if include_package_quality:
        package_sources = (
            _quality_seed_bank_examples(),
            _quality_corpus_examples(),
        )
    iterators = deque(
        iter(source)
        for source in (*package_sources,
            _curated_seed_examples(root),
            _knowledge_examples(root),
            _code_template_examples(root),
            _code_snippet_examples(root),
            _project_recipe_examples(root),
            _math_formula_examples(root),
            _translation_examples(root),
            _lexical_relation_examples(root),
            _technical_vocabulary_examples(root),
            _structured_domain_examples(root),
        )
    )
    seen: set[str] = set()
    source_counts: dict[str, int] = {}
    emitted = 0
    selected_sources = {
        str(source).casefold() for source in (include_sources or set()) if str(source)
    }
    while iterators:
        iterator = iterators.popleft()
        try:
            example = next(iterator)
        except StopIteration:
            continue
        iterators.append(iterator)
        if example.quality < minimum_quality:
            continue
        if selected_sources and example.source.casefold() not in selected_sources:
            continue
        digest = _example_digest(example)
        if digest in seen:
            continue
        seen.add(digest)
        if not _belongs_to_split(digest, split, validation_fraction):
            continue
        source_count = source_counts.get(example.source, 0)
        if max_examples_per_source and source_count >= max_examples_per_source:
            continue
        source_counts[example.source] = source_count + 1
        yield example
        emitted += 1
        if max_examples and emitted >= max_examples:
            return


def build_instruction_training_windows(
    tokenizer: CanriTokenizer,
    example: InstructionExample,
    *,
    context_length: int = 256,
    max_windows_per_example: int = 4,
) -> list[InstructionTrainingWindow]:
    """Encode one instruction with labels limited to its assistant completion."""

    context_length = max(32, int(context_length))
    target_length = context_length + 1
    prompt = (
        "<|user|>\n"
        + example.user.strip()
        + "\n<|assistant|>\n"
    )
    completion = example.assistant.strip() + "\n<|end|>"
    prompt_ids = tokenizer.encode(prompt, add_special_tokens=False)
    completion_ids = tokenizer.encode(completion, add_special_tokens=False)
    completion_ids.append(tokenizer.eos_id)

    maximum_prompt = max(16, context_length // 2)
    if len(prompt_ids) > maximum_prompt:
        head_size = max(8, maximum_prompt * 2 // 3)
        tail_size = maximum_prompt - head_size
        prompt_ids = prompt_ids[:head_size] + prompt_ids[-tail_size:]
    prefix = [tokenizer.bos_id, *prompt_ids]
    completion_capacity = target_length - len(prefix)
    if completion_capacity < 8:
        prefix = prefix[: target_length - 8]
        completion_capacity = 8

    windows: list[InstructionTrainingWindow] = []
    maximum_windows = max(1, int(max_windows_per_example))
    for offset in range(0, len(completion_ids), completion_capacity):
        if offset // completion_capacity >= maximum_windows:
            break
        completion_chunk = completion_ids[offset:offset + completion_capacity]
        sequence = prefix + completion_chunk
        sequence.extend([tokenizer.pad_id] * max(0, target_length - len(sequence)))
        sequence = sequence[:target_length]
        completion_target_start = len(prefix) - 1
        target_ids = list(sequence[1:])
        for index in range(len(target_ids)):
            if index < completion_target_start or target_ids[index] == tokenizer.pad_id:
                target_ids[index] = IGNORE_INDEX
        if all(token_id == IGNORE_INDEX for token_id in target_ids):
            continue
        windows.append(
            InstructionTrainingWindow(
                token_ids=tuple(sequence),
                target_ids=tuple(target_ids),
                source=example.source,
            )
        )
    return windows


def iter_instruction_training_windows(
    tokenizer: CanriTokenizer,
    *,
    data_root: Path = DATA_ROOT,
    context_length: int = 256,
    minimum_quality: float = 75.0,
    max_examples: int = 0,
    split: InstructionSplit = "train",
    validation_fraction: float = 0.05,
    shuffle_buffer: int = 0,
    seed: int = 42,
    max_windows_per_example: int = 4,
    max_examples_per_source: int = 0,
    curated_repeats: int = 1,
    include_sources: set[str] | None = None,
    include_package_quality: bool | None = None,
) -> Iterator[InstructionTrainingWindow]:
    """Build answer-focused windows while retaining a compact request prefix.

    Earlier training treated prompt tokens and answer tokens equally. Long user
    requests could therefore consume almost the entire context and teach very
    little answer generation. These windows mask prompt and padding labels, and
    split longer answers into bounded completion chunks.
    """

    context_length = max(32, int(context_length))
    examples: Iterable[InstructionExample] = iter_instruction_examples(
        data_root,
        minimum_quality=minimum_quality,
        max_examples=max_examples,
        split=split,
        validation_fraction=validation_fraction,
        max_examples_per_source=max(0, int(max_examples_per_source)),
        include_sources=include_sources,
        include_package_quality=include_package_quality,
    )
    if shuffle_buffer:
        examples = _buffered_shuffle(
            examples,
            buffer_size=shuffle_buffer,
            seed=seed,
        )

    for example in examples:
        example_windows = build_instruction_training_windows(
            tokenizer,
            example,
            context_length=context_length,
            max_windows_per_example=max_windows_per_example,
        )
        repeats = (
            _training_repeats_for_source(example.source, curated_repeats)
            if split == "train"
            else 1
        )
        for _ in range(repeats):
            yield from example_windows


def iter_instruction_token_windows(
    tokenizer: CanriTokenizer,
    *,
    data_root: Path = DATA_ROOT,
    context_length: int = 256,
    minimum_quality: float = 75.0,
    max_examples: int = 0,
    split: InstructionSplit = "all",
    validation_fraction: float = 0.05,
    include_sources: set[str] | None = None,
) -> Iterator[list[int]]:
    """Compatibility iterator returning unmasked fixed-size token sequences."""

    for window in iter_instruction_training_windows(
        tokenizer,
        data_root=data_root,
        context_length=context_length,
        minimum_quality=minimum_quality,
        max_examples=max_examples,
        split=split,
        validation_fraction=validation_fraction,
        include_sources=include_sources,
    ):
        yield list(window.token_ids)
