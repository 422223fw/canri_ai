from __future__ import annotations

import json
import shutil
import sqlite3
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path

from main_ai_canri.domain_packages.local_llm.dataset import (
    inventory_data_sources,
    iter_all_data_texts,
    iter_balanced_token_windows,
)
from main_ai_canri.domain_packages.local_llm.instruction_dataset import (
    IGNORE_INDEX,
    iter_instruction_examples,
    iter_instruction_training_windows,
    iter_instruction_token_windows,
)
from main_ai_canri.domain_packages.local_llm.sealed_evaluate import (
    validate_python_behavior,
)
from main_ai_canri.domain_packages.local_llm.inference import (
    _blocked_ngram_tokens,
    _fit_prompt,
)
from main_ai_canri.domain_packages.local_llm.model.transformer import (
    CanriConfig,
    build_model,
    require_torch,
)
from main_ai_canri.domain_packages.local_llm.transfer import transfer_state_dict
from main_ai_canri.domain_packages.local_llm.tokenizer import (
    HYBRID_MODE,
    CanriTokenizer,
)


TEST_ROOT = Path(__file__).resolve().parent
RUNTIME_ROOT = TEST_ROOT / "_native_llm_test_runtime"


@contextmanager
def workspace_test_directory():
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    path = RUNTIME_ROOT / uuid.uuid4().hex
    path.mkdir()
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


class HybridTokenizerTests(unittest.TestCase):
    def test_hybrid_tokenizer_round_trip_and_persistence(self):
        text = "hello hello, שלום; print(value)"
        tokenizer = CanriTokenizer.from_texts([text], max_vocab_size=256)
        self.assertEqual(tokenizer.mode, HYBRID_MODE)
        self.assertEqual(tokenizer.decode(tokenizer.encode(text)), text)

        with workspace_test_directory() as directory:
            path = directory / "tokenizer.json"
            tokenizer.save(path, metadata={"test": True})
            restored = CanriTokenizer.load(path)
            self.assertEqual(restored.mode, HYBRID_MODE)
            self.assertEqual(restored.decode(restored.encode(text)), text)
            self.assertTrue(restored.metadata["test"])

    def test_prompt_fitting_preserves_the_beginning_and_end(self):
        values = list(range(100))
        fitted = _fit_prompt(values, 20)
        self.assertEqual(len(fitted), 20)
        self.assertEqual(fitted[:12], values[:12])
        self.assertEqual(fitted[-8:], values[-8:])

    def test_repeated_ngram_next_token_is_blocked(self):
        generated = [1, 2, 3, 1, 2]
        self.assertEqual(_blocked_ngram_tokens(generated, 3), {3})

    def test_tokenizer_expansion_preserves_existing_token_ids(self):
        base = CanriTokenizer.from_texts(["alpha beta"], max_vocab_size=256)
        expanded = CanriTokenizer.expanded_from_texts(
            base,
            ["alpha beta gamma delta epsilon"],
            max_vocab_size=300,
        )
        self.assertEqual(expanded.vocabulary[: len(base)], base.vocabulary)
        self.assertEqual(base.token_to_id["alpha"], expanded.token_to_id["alpha"])
        self.assertGreater(len(expanded), len(base))

    def test_weight_transfer_copies_overlap_and_bootstraps_new_layer(self):
        torch, _ = require_torch()
        torch.manual_seed(1)
        source = build_model(
            CanriConfig(
                vocab_size=64,
                context_length=32,
                embedding_size=32,
                layers=1,
                heads=4,
            )
        )
        target = build_model(
            CanriConfig(
                vocab_size=72,
                context_length=40,
                embedding_size=40,
                layers=2,
                heads=5,
            )
        )
        source_state = source.state_dict()
        source_state["token_embedding.weight"].fill_(0.25)
        target_state = target.state_dict()
        report = transfer_state_dict(
            target_state,
            source_state,
            source_layers=1,
        )
        self.assertTrue(
            torch.allclose(
                target_state["token_embedding.weight"][:64, :32],
                source_state["token_embedding.weight"],
            )
        )
        self.assertTrue(
            torch.allclose(
                target_state["blocks.layers.1.norm1.weight"][:32],
                source_state["blocks.layers.0.norm1.weight"],
            )
        )
        self.assertGreater(report["transferred_state_elements"], 0)
        self.assertGreater(report["cloned_layer_tensors"], 0)


class StreamingDatasetTests(unittest.TestCase):
    def test_json_jsonl_and_sqlite_are_streamed(self):
        with workspace_test_directory() as root:
            (root / "sample.json").write_text(
                json.dumps({"title": "Gravity", "summary": "Gravity attracts masses."}),
                encoding="utf-8",
            )
            (root / "sample.jsonl").write_text(
                json.dumps({"title": "Python", "summary": "Python is a language."}) + "\n",
                encoding="utf-8",
            )
            database = root / "sample.sqlite3"
            connection = sqlite3.connect(database)
            connection.execute("CREATE TABLE facts (name TEXT, value TEXT)")
            connection.execute("INSERT INTO facts VALUES (?, ?)", ("Earth", "planet"))
            connection.commit()
            connection.close()

            inventory = inventory_data_sources(root)
            self.assertEqual(inventory["files"], 3)
            self.assertEqual(set(inventory["by_kind"]), {"json", "jsonl", "sqlite"})

            texts = list(iter_all_data_texts(root, chunk_chars=4096))
            joined = "".join(texts)
            self.assertIn("Gravity", joined)
            self.assertIn("Python", joined)
            self.assertIn("Earth", joined)

            tokenizer = CanriTokenizer.from_texts(texts, max_vocab_size=256)
            windows = list(
                iter_balanced_token_windows(
                    tokenizer,
                    data_root=root,
                    context_length=32,
                    samples_per_source=1,
                    shuffle_sources=False,
                )
            )
            self.assertEqual(len(windows), 3)
            self.assertTrue(all(len(window) == 33 for window in windows))


class InstructionDatasetTests(unittest.TestCase):
    def test_package_quality_is_not_injected_into_a_custom_data_root(self):
        with workspace_test_directory() as root:
            payload = {
                "examples": [
                    {
                        "user": "Say hello.",
                        "assistant": "Hello.",
                        "quality": 100,
                    }
                ]
            }
            (root / "Local_llm_instruction_seeds.json").write_text(
                json.dumps(payload), encoding="utf-8"
            )
            examples = list(iter_instruction_examples(root))
            self.assertEqual(len(examples), 1)
            self.assertEqual(examples[0].source, "Local_llm_instruction_seeds.json")

    def test_only_trusted_knowledge_becomes_instruction_data(self):
        with workspace_test_directory() as root:
            trusted = {
                "title": "Gravity",
                "summary": "Gravity is the attraction between masses and shapes planetary motion.",
                "source_name": "Trusted reference",
                "source_trust_score": 90,
            }
            weak = {
                "title": "Rumor",
                "summary": "This unsupported claim should never become a training answer.",
                "source_name": "Unknown",
                "source_trust_score": 20,
            }
            (root / "Knowledge_database.jsonl").write_text(
                json.dumps(trusted) + "\n" + json.dumps(weak) + "\n",
                encoding="utf-8",
            )
            examples = list(iter_instruction_examples(root))
            self.assertEqual(len(examples), 1)
            self.assertIn("Gravity", examples[0].user)
            self.assertNotIn("unsupported", examples[0].assistant)

            tokenizer = CanriTokenizer.from_texts(
                [examples[0].formatted()],
                max_vocab_size=256,
            )
            windows = list(
                iter_instruction_token_windows(
                    tokenizer,
                    data_root=root,
                    context_length=64,
                )
            )
            self.assertGreaterEqual(len(windows), 1)
            self.assertTrue(all(len(window) == 65 for window in windows))

    def test_instruction_labels_only_train_the_assistant_completion(self):
        with workspace_test_directory() as root:
            payload = {
                "examples": [
                    {
                        "user": "Repeat the requested result.",
                        "assistant": "The requested result is complete.",
                        "quality": 100,
                    }
                ]
            }
            (root / "Local_llm_instruction_seeds.json").write_text(
                json.dumps(payload), encoding="utf-8"
            )
            tokenizer = CanriTokenizer.from_texts(
                ["Repeat the requested result. The requested result is complete."],
                max_vocab_size=256,
            )
            windows = list(
                iter_instruction_training_windows(
                    tokenizer,
                    data_root=root,
                    context_length=64,
                    split="all",
                )
            )
            self.assertEqual(len(windows), 1)
            self.assertEqual(len(windows[0].token_ids), 65)
            self.assertEqual(len(windows[0].target_ids), 64)
            self.assertIn(IGNORE_INDEX, windows[0].target_ids)
            self.assertTrue(
                any(token != IGNORE_INDEX for token in windows[0].target_ids)
            )

    def test_train_and_validation_examples_do_not_overlap(self):
        with workspace_test_directory() as root:
            records = [
                {
                    "user": f"Question {index}",
                    "assistant": f"Answer {index}",
                    "quality": 100,
                }
                for index in range(100)
            ]
            (root / "Local_llm_instruction_seeds.json").write_text(
                json.dumps({"examples": records}), encoding="utf-8"
            )
            train = {
                (item.user, item.assistant)
                for item in iter_instruction_examples(
                    root, split="train", validation_fraction=0.2
                )
            }
            validation = {
                (item.user, item.assistant)
                for item in iter_instruction_examples(
                    root, split="validation", validation_fraction=0.2
                )
            }
            self.assertTrue(train)
            self.assertTrue(validation)
            self.assertFalse(train & validation)
            self.assertEqual(len(train | validation), 100)

    def test_instruction_sources_can_be_selected_for_curriculum_training(self):
        with workspace_test_directory() as root:
            (root / "Local_llm_instruction_seeds.json").write_text(
                json.dumps(
                    {
                        "examples": [
                            {
                                "user": "Say hello.",
                                "assistant": "Hello.",
                                "quality": 100,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (root / "Math_formulas.json").write_text(
                json.dumps(
                    {
                        "formulas": [
                            {
                                "name": "sum",
                                "formula": "a + b",
                                "verification": "recompute",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            examples = list(
                iter_instruction_examples(
                    root,
                    split="all",
                    include_sources={"Local_llm_instruction_seeds.json"},
                )
            )
            self.assertEqual(len(examples), 1)
            self.assertEqual(examples[0].source, "Local_llm_instruction_seeds.json")


class SealedEvaluationTests(unittest.TestCase):
    def test_safe_generated_function_is_executed_against_behavior_cases(self):
        result = validate_python_behavior(
            "def is_even(number):\n    return number % 2 == 0",
            {
                "required_function": "is_even",
                "calls": [
                    {"args": [2], "expected": True},
                    {"args": [7], "expected": False},
                ],
            },
        )
        self.assertTrue(result["syntax_ok"])
        self.assertTrue(result["passed"])

    def test_unsafe_generated_function_is_rejected_before_execution(self):
        result = validate_python_behavior(
            "import os\ndef is_even(number):\n    return number % 2 == 0",
            {
                "required_function": "is_even",
                "calls": [{"args": [2], "expected": True}],
            },
        )
        self.assertFalse(result["passed"])
        self.assertIn("Only function definitions", result["error"])

    def test_quality_corpus_has_no_exact_sealed_prompt(self):
        package = (
            Path(__file__).resolve().parents[1]
            / "main_ai_canri"
            / "domain_packages"
            / "local_llm"
        )
        holdout = json.loads(
            (package / "evaluation" / "sealed_holdout_v2.json").read_text(
                encoding="utf-8"
            )
        )
        sealed = {
            " ".join(str(case["prompt"]).casefold().split())
            for case in holdout["cases"]
        }
        observed = set()
        for path in (package / "quality_corpus").glob("*.jsonl"):
            with path.open(encoding="utf-8") as handle:
                for line in handle:
                    record = json.loads(line)
                    observed.add(" ".join(str(record["user"]).casefold().split()))
        self.assertTrue(sealed)
        self.assertFalse(sealed & observed)


if __name__ == "__main__":
    unittest.main()
