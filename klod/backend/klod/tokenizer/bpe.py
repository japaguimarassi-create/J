from __future__ import annotations

import base64
import json
from collections import Counter
from pathlib import Path
from typing import Iterable, Sequence


class BytePairTokenizer:
    FORMAT_VERSION = 1
    BASE_VOCAB_SIZE = 256

    def __init__(self) -> None:
        self._token_bytes = [bytes([value]) for value in range(256)]
        self._merges: list[tuple[int, int, int]] = []

    @property
    def vocab_size(self) -> int:
        return len(self._token_bytes)

    @staticmethod
    def _merge_pair(sequence: Sequence[int], pair: tuple[int, int], new_id: int) -> list[int]:
        result: list[int] = []
        index = 0
        while index < len(sequence):
            if index + 1 < len(sequence) and (sequence[index], sequence[index + 1]) == pair:
                result.append(new_id)
                index += 2
            else:
                result.append(sequence[index])
                index += 1
        return result

    def train(self, texts: Iterable[str], vocab_size: int = 2048, min_frequency: int = 2) -> "BytePairTokenizer":
        if vocab_size < 256 or min_frequency < 2:
            raise ValueError("vocab_size must be >= 256 and min_frequency must be >= 2")
        sequences = [list(text.encode("utf-8")) for text in texts]
        self._token_bytes = [bytes([value]) for value in range(256)]
        self._merges = []
        while self.vocab_size < vocab_size:
            counts: Counter[tuple[int, int]] = Counter()
            for sequence in sequences:
                counts.update(zip(sequence, sequence[1:]))
            if not counts:
                break
            pair, frequency = min(counts.items(), key=lambda item: (-item[1], item[0]))
            if frequency < min_frequency:
                break
            new_id = self.vocab_size
            left, right = pair
            self._token_bytes.append(self._token_bytes[left] + self._token_bytes[right])
            self._merges.append((left, right, new_id))
            sequences = [self._merge_pair(sequence, pair, new_id) for sequence in sequences]
        return self

    def encode(self, text: str) -> list[int]:
        if not isinstance(text, str):
            raise TypeError("encode expects a string")
        sequence = list(text.encode("utf-8"))
        for left, right, new_id in self._merges:
            sequence = self._merge_pair(sequence, (left, right), new_id)
        return sequence

    def decode(self, token_ids: Sequence[int]) -> str:
        payload = bytearray()
        for token_id in token_ids:
            if not isinstance(token_id, int) or token_id < 0 or token_id >= self.vocab_size:
                raise ValueError(f"Invalid token ID: {token_id!r}")
            payload.extend(self._token_bytes[token_id])
        return payload.decode("utf-8", errors="strict")

    def save(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "format_version": self.FORMAT_VERSION,
            "vocab_size": self.vocab_size,
            "tokens_base64": [base64.b64encode(token).decode("ascii") for token in self._token_bytes],
            "merges": [list(merge) for merge in self._merges],
        }
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_text(json.dumps(data), encoding="utf-8")
        temporary.replace(destination)

    @classmethod
    def load(cls, path: str | Path) -> "BytePairTokenizer":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("format_version") != cls.FORMAT_VERSION:
            raise ValueError("Unsupported tokenizer format version")
        tokenizer = cls()
        tokenizer._token_bytes = [base64.b64decode(item, validate=True) for item in data["tokens_base64"]]
        tokenizer._merges = [tuple(map(int, merge)) for merge in data["merges"]]
        if tokenizer.vocab_size != int(data["vocab_size"]) or tokenizer.vocab_size < 256:
            raise ValueError("Serialized vocabulary size is invalid")
        for left, right, new_id in tokenizer._merges:
            if left >= new_id or right >= new_id or new_id >= tokenizer.vocab_size:
                raise ValueError("Tokenizer merge table is invalid")
            if tokenizer._token_bytes[new_id] != tokenizer._token_bytes[left] + tokenizer._token_bytes[right]:
                raise ValueError("Tokenizer merge payload is inconsistent")
        return tokenizer
