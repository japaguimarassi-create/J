from __future__ import annotations

import base64
import json
from collections import Counter
from pathlib import Path
from typing import Iterable, Sequence


class BytePairTokenizer:
    FORMAT_VERSION = 2
    BASE_VOCAB_SIZE = 256
    SPECIAL_TOKENS = ("<pad>", "<bos>", "<eos>", "<unk>")

    def __init__(self) -> None:
        self._token_bytes: list[bytes] = [bytes([value]) for value in range(256)]
        self._merges: list[tuple[int, int, int]] = []

    @property
    def vocab_size(self) -> int:
        return len(self._token_bytes) + len(self.SPECIAL_TOKENS)

    @property
    def special_token_ids(self) -> dict[str, int]:
        offset = len(self._token_bytes)
        return {token: offset + index for index, token in enumerate(self.SPECIAL_TOKENS)}

    @staticmethod
    def _merge_pair(sequence: Sequence[int], pair: tuple[int, int], new_id: int) -> list[int]:
        merged: list[int] = []
        index = 0
        while index < len(sequence):
            if index + 1 < len(sequence) and (sequence[index], sequence[index + 1]) == pair:
                merged.append(new_id)
                index += 2
            else:
                merged.append(sequence[index])
                index += 1
        return merged

    def train(
        self,
        texts: Iterable[str],
        vocab_size: int = 2048,
        min_frequency: int = 2,
    ) -> "BytePairTokenizer":
        minimum = self.BASE_VOCAB_SIZE + len(self.SPECIAL_TOKENS)
        if vocab_size < minimum:
            raise ValueError(f"vocab_size must be at least {minimum}")
        if min_frequency < 2:
            raise ValueError("min_frequency must be at least 2")

        sequences = [list(text.encode("utf-8")) for text in texts]
        self._token_bytes = [bytes([value]) for value in range(256)]
        self._merges = []

        while self.vocab_size < vocab_size:
            counts: Counter[tuple[int, int]] = Counter()
            for sequence in sequences:
                counts.update(zip(sequence, sequence[1:]))
            if not counts:
                break
            best_pair, frequency = min(counts.items(), key=lambda item: (-item[1], item[0]))
            if frequency < min_frequency:
                break

            new_id = len(self._token_bytes)
            left, right = best_pair
            self._token_bytes.append(self._token_bytes[left] + self._token_bytes[right])
            self._merges.append((left, right, new_id))
            sequences = [self._merge_pair(sequence, best_pair, new_id) for sequence in sequences]

        return self

    def encode(self, text: str, add_bos: bool = False, add_eos: bool = False) -> list[int]:
        if not isinstance(text, str):
            raise TypeError("encode expects a string")
        sequence = list(text.encode("utf-8"))
        for left, right, new_id in self._merges:
            sequence = self._merge_pair(sequence, (left, right), new_id)
        special_ids = self.special_token_ids
        if add_bos:
            sequence.insert(0, special_ids["<bos>"])
        if add_eos:
            sequence.append(special_ids["<eos>"])
        return sequence

    def decode(
        self,
        token_ids: Sequence[int],
        skip_special_tokens: bool = False,
        errors: str = "strict",
    ) -> str:
        if errors not in {"strict", "replace", "ignore", "backslashreplace"}:
            raise ValueError("Unsupported UTF-8 decoding error mode")
        byte_buffer = bytearray()
        output: list[str] = []
        special_offset = len(self._token_bytes)
        for token_id in token_ids:
            if not isinstance(token_id, int) or token_id < 0 or token_id >= self.vocab_size:
                raise ValueError(f"Invalid token ID: {token_id!r}")
            if token_id < special_offset:
                byte_buffer.extend(self._token_bytes[token_id])
                continue
            if not skip_special_tokens:
                if byte_buffer:
                    output.append(byte_buffer.decode("utf-8", errors=errors))
                    byte_buffer.clear()
                output.append(self.SPECIAL_TOKENS[token_id - special_offset])
        if byte_buffer:
            output.append(byte_buffer.decode("utf-8", errors=errors))
        return "".join(output)

    def save(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "format_version": self.FORMAT_VERSION,
            "vocab_size": self.vocab_size,
            "special_tokens": list(self.SPECIAL_TOKENS),
            "tokens_base64": [base64.b64encode(token).decode("ascii") for token in self._token_bytes],
            "merges": [list(merge) for merge in self._merges],
        }
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        temporary.replace(destination)

    @classmethod
    def load(cls, path: str | Path) -> "BytePairTokenizer":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("format_version") != cls.FORMAT_VERSION:
            raise ValueError("Unsupported tokenizer format version")
        if tuple(data.get("special_tokens", ())) != cls.SPECIAL_TOKENS:
            raise ValueError("Tokenizer special-token definitions are incompatible")
        tokenizer = cls()
        tokenizer._token_bytes = [base64.b64decode(item, validate=True) for item in data["tokens_base64"]]
        tokenizer._merges = [tuple(map(int, merge)) for merge in data["merges"]]
        if tokenizer.vocab_size != int(data["vocab_size"]):
            raise ValueError("Tokenizer vocabulary size does not match serialized tokens")
        if len(tokenizer._token_bytes) < cls.BASE_VOCAB_SIZE:
            raise ValueError("Tokenizer is missing base byte tokens")
        for left, right, new_id in tokenizer._merges:
            if left >= new_id or right >= new_id or new_id >= len(tokenizer._token_bytes):
                raise ValueError("Tokenizer merge table is invalid")
            if tokenizer._token_bytes[new_id] != tokenizer._token_bytes[left] + tokenizer._token_bytes[right]:
                raise ValueError("Tokenizer merge payload is inconsistent")
        return tokenizer
