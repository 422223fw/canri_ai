"""Build deterministic, inspectable instruction shards for native CANRI.

The builder accepts only trusted structured sources and human-authored seeds.
It never imports old CANRI chat answers, queues, memory, or model generations.
The sealed holdout lives outside the output directory and exact holdout prompts
are rejected before a training shard is written.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

from .dataset import DATA_ROOT
from .behavior_corpus import iter_behavior_examples, iter_code_behavior_examples
from .instruction_dataset import (
    InstructionExample,
    PACKAGE_ROOT,
    QUALITY_CORPUS_ROOT,
    _code_snippet_examples,
    _code_template_examples,
    _curated_seed_examples,
    _knowledge_examples,
    _lexical_relation_examples,
    _math_formula_examples,
    _project_recipe_examples,
    _quality_seed_bank_examples,
    _structured_domain_examples,
    _technical_vocabulary_examples,
    _translation_examples,
)


DEFAULT_HOLDOUT = PACKAGE_ROOT / "evaluation" / "sealed_holdout_v2.json"
DEFAULT_MANIFEST = QUALITY_CORPUS_ROOT / "manifest.json"
REJECTED_PHRASES = (
    "production draft",
    "not implemented",
    "placeholder",
    "review it before running",
    "here is a first code structure draft",
)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build CANRI's clean corpus shards.")
    parser.add_argument("--data-root", type=Path, default=DATA_ROOT)
    parser.add_argument("--output-root", type=Path, default=QUALITY_CORPUS_ROOT)
    parser.add_argument("--holdout", type=Path, default=DEFAULT_HOLDOUT)
    parser.add_argument("--knowledge-limit", type=int, default=6_000)
    parser.add_argument("--code-template-limit", type=int, default=6_000)
    parser.add_argument("--code-snippet-limit", type=int, default=4_000)
    parser.add_argument("--other-source-limit", type=int, default=3_000)
    return parser


def _normalized(value: str) -> str:
    return " ".join(str(value or "").casefold().split())


def _digest(user: str, assistant: str = "") -> str:
    return hashlib.sha256(
        (_normalized(user) + "\0" + _normalized(assistant)).encode("utf-8")
    ).hexdigest()


def _load_holdout_prompts(path: Path) -> tuple[set[str], str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases", []) if isinstance(payload, dict) else []
    prompts = {
        _normalized(item.get("prompt"))
        for item in cases
        if isinstance(item, dict) and str(item.get("prompt") or "").strip()
    }
    return prompts, hashlib.sha256(path.read_bytes()).hexdigest()


def _python_blocks(text: str) -> Iterator[str]:
    pattern = re.compile(r"```(?:python|py)\s*\n(.*?)```", re.I | re.S)
    for match in pattern.finditer(text):
        yield match.group(1).strip()


def _valid_example(example: InstructionExample, holdout_prompts: set[str]) -> bool:
    user = str(example.user or "").strip()
    assistant = str(example.assistant or "").strip()
    if not (2 <= len(user) <= 1_200 and 1 <= len(assistant) <= 4_000):
        return False
    if _normalized(user) in holdout_prompts:
        return False
    lowered = assistant.casefold()
    if any(phrase in lowered for phrase in REJECTED_PHRASES):
        return False
    for code in _python_blocks(assistant):
        try:
            ast.parse(code)
        except SyntaxError:
            return False
    return True


def _math_examples() -> Iterator[InstructionExample]:
    for index in range(400):
        left = 7 + index % 89
        right = 3 + (index * 7) % 47
        total = left + right
        yield InstructionExample(
            user=f"Calculate {left} + {right} and give only the result.",
            assistant=str(total),
            source="generated_exact_math_en",
            quality=100.0,
        )

        larger = left + right + 5
        difference = larger - right
        yield InstructionExample(
            user=f"Subtract {right} from {larger} and show the calculation.",
            assistant=f"{larger} - {right} = {difference}.",
            source="generated_exact_math_en",
            quality=100.0,
        )

        factor_a = 2 + index % 18
        factor_b = 2 + (index * 5) % 17
        product = factor_a * factor_b
        yield InstructionExample(
            user=f"What is {factor_a} multiplied by {factor_b}?",
            assistant=f"{factor_a} × {factor_b} = {product}.",
            source="generated_exact_math_en",
            quality=100.0,
        )

        divisor = 2 + index % 19
        quotient = 2 + (index * 3) % 31
        dividend = divisor * quotient
        yield InstructionExample(
            user=f"Divide {dividend} by {divisor}.",
            assistant=f"{dividend} ÷ {divisor} = {quotient}.",
            source="generated_exact_math_en",
            quality=100.0,
        )

        percent = (5, 10, 20, 25, 50)[index % 5]
        whole = 20 * (2 + index % 40)
        result = percent * whole / 100
        rendered = str(int(result)) if result.is_integer() else str(result)
        yield InstructionExample(
            user=f"Calculate {percent} percent of {whole} and show the formula.",
            assistant=(
                f"{percent} percent is {percent / 100:g}. "
                f"{percent / 100:g} × {whole} = {rendered}."
            ),
            source="generated_exact_math_en",
            quality=100.0,
        )

        solution = 1 + index % 30
        coefficient = 2 + index % 8
        constant = (index * 3) % 17
        result_side = coefficient * solution + constant
        yield InstructionExample(
            user=(
                f"Solve {coefficient}x + {constant} = {result_side} "
                "and verify the solution."
            ),
            assistant=(
                f"Subtract {constant}: {coefficient}x = {coefficient * solution}. "
                f"Divide by {coefficient}: x = {solution}. Verification: "
                f"{coefficient} × {solution} + {constant} = {result_side}."
            ),
            source="generated_exact_math_en",
            quality=100.0,
        )

    for index in range(200):
        left = 10 + index % 70
        right = 4 + (index * 3) % 30
        yield InstructionExample(
            user=f"חשב כמה הם {left} ועוד {right} והחזר רק את התוצאה.",
            assistant=str(left + right),
            source="generated_exact_math_he",
            quality=100.0,
        )
        percent = (10, 20, 25, 50)[index % 4]
        whole = 40 * (1 + index % 25)
        result = percent * whole // 100
        yield InstructionExample(
            user=f"חשב {percent} אחוז מתוך {whole} והראה את החישוב.",
            assistant=(
                f"ממירים {percent} אחוז ל־{percent / 100:g} ומכפילים: "
                f"{percent / 100:g} × {whole} = {result}."
            ),
            source="generated_exact_math_he",
            quality=100.0,
        )
        solution = 1 + index % 20
        coefficient = 2 + index % 7
        constant = index % 11
        result_side = coefficient * solution + constant
        yield InstructionExample(
            user=f"פתור {coefficient}x + {constant} = {result_side} ובדוק את הפתרון.",
            assistant=(
                f"מחסרים {constant} ומקבלים {coefficient}x = {coefficient * solution}. "
                f"מחלקים ב־{coefficient} ומקבלים x = {solution}. בדיקה: "
                f"{coefficient} × {solution} + {constant} = {result_side}."
            ),
            source="generated_exact_math_he",
            quality=100.0,
        )


def _knowledge_variant(example: InstructionExample) -> InstructionExample | None:
    match = re.match(
        r"(?:What is|Explain|Give a concise, reliable overview of)\s+(.+?)(?:\?| clearly| clearly and accurately|\.)?$",
        example.user,
        flags=re.I,
    )
    if not match:
        return None
    title = match.group(1).strip().rstrip(".")
    return InstructionExample(
        user=f"Could you give me a reliable plain-language summary of {title}?",
        assistant=example.assistant,
        source=example.source,
        quality=example.quality,
    )


def _bounded(values: Iterable[InstructionExample], limit: int) -> Iterator[InstructionExample]:
    for index, value in enumerate(values):
        if index >= max(0, int(limit)):
            return
        yield value


def _source_examples(args: argparse.Namespace) -> Iterator[InstructionExample]:
    data_root = Path(args.data_root)
    yield from iter_behavior_examples()
    yield from iter_code_behavior_examples()
    yield from _quality_seed_bank_examples()
    yield from _curated_seed_examples(data_root)

    for example in _bounded(_knowledge_examples(data_root), args.knowledge_limit):
        yield example
        variant = _knowledge_variant(example)
        if variant is not None:
            yield variant

    yield from _bounded(_code_template_examples(data_root), args.code_template_limit)
    yield from _bounded(_code_snippet_examples(data_root), args.code_snippet_limit)
    yield from _bounded(_project_recipe_examples(data_root), args.other_source_limit)
    yield from _bounded(_math_formula_examples(data_root), args.other_source_limit)
    yield from _math_examples()
    yield from _bounded(_translation_examples(data_root), args.other_source_limit)
    yield from _bounded(_lexical_relation_examples(data_root), args.other_source_limit)
    yield from _bounded(_technical_vocabulary_examples(data_root), args.other_source_limit)
    yield from _bounded(_structured_domain_examples(data_root), args.other_source_limit)


def _category(example: InstructionExample) -> str:
    source = example.source.casefold()
    user = example.user.casefold()
    if source == "generated_behavior_conversation_en":
        return "conversation_en"
    if source == "generated_behavior_conversation_he":
        return "conversation_he"
    if source == "generated_behavior_code":
        return "code_behavior"
    if source in {"generated_behavior_task_following", "generated_behavior_context"}:
        return "task_following"
    if source in {"generated_behavior_science", "generated_behavior_emotional_support"}:
        return "conversation_en"
    if source.endswith("quality_seed_bank.json"):
        if any("\u0590" <= char <= "\u05ff" for char in example.user):
            return "conversation_he"
        return "conversation_en"
    if "math" in source:
        return "math"
    if source in {"code.json", "code_library_templates.json"}:
        return "code"
    if "recipe" in source or "requirement" in user:
        return "task_following"
    if "knowledge" in source or "scan_database" in source:
        return "knowledge"
    if "translation" in source or "synonym" in source or "antonym" in source:
        return "language"
    if any(value in source for value in ("technical", "hardware", "unit")):
        return "technical"
    return "structured_knowledge"


def _atomic_write_jsonl(path: Path, records: list[dict]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")
    temporary.replace(path)


def build(args: argparse.Namespace) -> dict:
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    holdout_prompts, holdout_sha256 = _load_holdout_prompts(Path(args.holdout))
    by_category: dict[str, list[dict]] = defaultdict(list)
    seen: set[str] = set()
    rejected = 0
    for example in _source_examples(args):
        if not _valid_example(example, holdout_prompts):
            rejected += 1
            continue
        fingerprint = _digest(example.user, example.assistant)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        category = _category(example)
        by_category[category].append(
            {
                "id": fingerprint[:20],
                "category": category,
                "user": example.user,
                "assistant": example.assistant,
                "origin": example.source,
                "quality": round(float(example.quality), 2),
            }
        )

    shards = []
    for category in sorted(by_category):
        records = sorted(by_category[category], key=lambda item: item["id"])
        destination = output_root / f"{category}.jsonl"
        _atomic_write_jsonl(destination, records)
        shards.append(
            {
                "file": destination.name,
                "examples": len(records),
                "bytes": destination.stat().st_size,
                "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            }
        )

    manifest = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "builder": "build_quality_corpus.py",
        "training_only": True,
        "old_chat_answers_used": False,
        "model_generated_answers_used": False,
        "sealed_holdout": str(Path(args.holdout).resolve()),
        "sealed_holdout_sha256": holdout_sha256,
        "sealed_prompt_count": len(holdout_prompts),
        "exact_holdout_prompts_in_training": 0,
        "examples": sum(item["examples"] for item in shards),
        "bytes": sum(item["bytes"] for item in shards),
        "rejected_examples": rejected,
        "shards": shards,
    }
    manifest_path = output_root / "manifest.json"
    temporary = manifest_path.with_name(manifest_path.name + ".tmp")
    temporary.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(manifest_path)
    return manifest


def main() -> int:
    args = make_parser().parse_args()
    try:
        result = build(args)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
