from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main_ai_canri.domain_packages.local_llm.instruction_dataset import (
    _training_repeats_for_source,
)
from main_ai_canri.domain_packages.local_llm.inference import (
    _utf8_continuations_for_start,
)
from main_ai_canri.domain_packages.local_llm.model.transformer import require_torch
from main_ai_canri.domain_packages.local_llm.tokenizer import (
    BYTE_HYBRID_MODE,
    CanriTokenizer,
)
from main_ai_canri.domain_packages.local_llm.transfer import _copy_token_rows


class LocalLLMV3Tests(unittest.TestCase):
    def test_byte_tokenizer_round_trips_multilingual_code(self):
        tokenizer = CanriTokenizer.from_byte_fallback_texts(
            ["Hello world", "שלום עולם", "print(value)"],
            max_vocab_size=512,
        )
        value = 'שלום, Canri!\nprint("ok")'

        encoded = tokenizer.encode(value, add_special_tokens=False)

        self.assertEqual(tokenizer.mode, BYTE_HYBRID_MODE)
        self.assertNotIn(tokenizer.unk_id, encoded)
        self.assertEqual(tokenizer.decode(encoded), value)

    def test_instruction_markers_are_atomic_in_v3(self):
        tokenizer = CanriTokenizer.from_byte_fallback_texts(
            ["answer"], max_vocab_size=512
        )

        encoded = tokenizer.encode("<|assistant|>\nanswer", add_special_tokens=False)

        self.assertEqual(encoded[0], tokenizer.token_to_id["<|assistant|>"])

    def test_utf8_generation_state_recognizes_valid_leading_bytes(self):
        self.assertEqual(_utf8_continuations_for_start(ord("A")), 0)
        self.assertEqual(_utf8_continuations_for_start(0xD7), 1)
        self.assertEqual(_utf8_continuations_for_start(0xE2), 2)
        self.assertEqual(_utf8_continuations_for_start(0xF1), 3)
        self.assertEqual(_utf8_continuations_for_start(0x80), -1)

    def test_weight_transfer_maps_embeddings_by_token_identity(self):
        torch, _ = require_torch()
        source = CanriTokenizer(["<pad>", "<unk>", "<bos>", "<eos>", "cat", "dog"])
        target = CanriTokenizer(["<pad>", "<unk>", "<bos>", "<eos>", "dog", "new", "cat"])
        source_rows = torch.arange(18, dtype=torch.float32).reshape(6, 3)
        target_rows = torch.full((7, 5), -1.0)

        copied, matched = _copy_token_rows(
            target_rows,
            source_rows,
            source_tokenizer=source,
            target_tokenizer=target,
        )

        self.assertEqual(matched, 6)
        self.assertEqual(copied, 18)
        self.assertTrue(torch.equal(target_rows[4, :3], source_rows[5]))
        self.assertTrue(torch.equal(target_rows[6, :3], source_rows[4]))
        self.assertTrue(torch.equal(target_rows[5], torch.full((5,), -1.0)))

    def test_high_signal_sources_receive_more_training_repeats(self):
        self.assertEqual(
            _training_repeats_for_source("quality_corpus/conversation_en.jsonl", 12),
            12,
        )
        self.assertEqual(
            _training_repeats_for_source("quality_corpus/code_behavior.jsonl", 12),
            12,
        )
        self.assertEqual(
            _training_repeats_for_source("quality_corpus/task_following.jsonl", 12),
            6,
        )
        self.assertEqual(
            _training_repeats_for_source("quality_corpus/knowledge.jsonl", 12),
            1,
        )


if __name__ == "__main__":
    unittest.main()
