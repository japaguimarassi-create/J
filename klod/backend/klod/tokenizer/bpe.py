from __future__ import annotations

import base64
import json
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Iterable, Iterator, Sequence


class BytePairTokenizer:
    FORMAT_VERSION = 3
    BASE_VOCAB_SIZE = 256
    SPECIAL_TOKENS = ("<pad>", "<bos>", "<eos>", "<unk>")
    DEFAULT_VOCAB_SIZE = 32768
    DEFAULT_MAX_TOKEN_BYTES = 128

    def __init__(self) -> None:
        self._token_bytes: list[bytes | None] = [bytes([value]) for value in range(256)]
        self._special_ids = {token: 256 + index for index, token in enumerate(self.SPECIAL_TOKENS)}
        self._token_bytes.extend([None] * len(self.SPECIAL_TOKENS))
        self._merges: list[tuple[int, int, int]] = []
        self._merge_frequencies: list[int] = []

    @property
    def vocab_size(self) -> int:
        return len(self._token_bytes)

    @property
    def special_token_ids(self) -> dict[str, int]:
        return dict(self._special_ids)

    @property
    def merge_count(self) -> int:
        return len(self._merges)

    @property
    def unicode_data_version(self) -> str:
        return unicodedata.unidata_version

    def fingerprint(self, vocab_size: int | None = None) -> str:
        import hashlib

        limit = self.vocab_size if vocab_size is None else vocab_size
        if limit < self.BASE_VOCAB_SIZE + len(self.SPECIAL_TOKENS) or limit > self.vocab_size:
            raise ValueError("Fingerprint vocabulary limit is outside the tokenizer")
        payload = {
            "vocab_size": limit,
            "special_token_ids": {
                key: value for key, value in self._special_ids.items() if value < limit
            },
            "tokens": [
                None if token is None else token.hex()
                for token in self._token_bytes[:limit]
            ],
            "merges": [
                list(merge) for merge in self._merges if merge[2] < limit
            ],
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def _bytes_for_token(self, token_id: int) -> bytes:
        if token_id < 0 or token_id >= len(self._token_bytes):
            raise ValueError(f"Invalid token ID: {token_id}")
        value = self._token_bytes[token_id]
        if value is None:
            raise ValueError(f"Token ID {token_id} is reserved for a special token")
        return value

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

    def _learn_merges(
        self,
        sequences: list[list[int]],
        target_vocab_size: int,
        min_frequency: int,
        max_token_bytes: int,
    ) -> "BytePairTokenizer":
        while self.vocab_size < target_vocab_size:
            counts: Counter[tuple[int, int]] = Counter()
            for sequence in sequences:
                counts.update(zip(sequence, sequence[1:]))
            if not counts:
                break
            eligible: list[tuple[tuple[int, int], int]] = []
            for pair, frequency in counts.items():
                try:
                    combined_size = len(self._bytes_for_token(pair[0])) + len(self._bytes_for_token(pair[1]))
                except ValueError:
                    continue
                if combined_size <= max_token_bytes and frequency >= min_frequency:
                    eligible.append((pair, frequency))
            if not eligible:
                break
            best_pair, frequency = min(eligible, key=lambda item: (-item[1], item[0]))
            new_id = self.vocab_size
            merged_bytes = self._bytes_for_token(best_pair[0]) + self._bytes_for_token(best_pair[1])
            self._token_bytes.append(merged_bytes)
            self._merges.append((best_pair[0], best_pair[1], new_id))
            self._merge_frequencies.append(frequency)
            sequences = [self._merge_pair(sequence, best_pair, new_id) for sequence in sequences]
        return self

    def train(
        self,
        texts: Iterable[str],
        vocab_size: int = DEFAULT_VOCAB_SIZE,
        min_frequency: int = 2,
        max_token_bytes: int = DEFAULT_MAX_TOKEN_BYTES,
    ) -> "BytePairTokenizer":
        minimum = self.BASE_VOCAB_SIZE + len(self.SPECIAL_TOKENS)
        if vocab_size < minimum:
            raise ValueError(f"vocab_size must be at least {minimum}")
        if min_frequency < 2 or max_token_bytes < 2:
            raise ValueError("min_frequency must be at least 2 and max_token_bytes at least 2")
        materialized = list(texts)
        if not materialized:
            raise ValueError("Tokenizer training requires at least one text record")
        if any(not isinstance(text, str) for text in materialized):
            raise TypeError("Tokenizer training records must be strings")
        self.__init__()
        sequences = [list(text.encode("utf-8", errors="strict")) for text in materialized]
        return self._learn_merges(sequences, vocab_size, min_frequency, max_token_bytes)

    def extend(
        self,
        texts: Iterable[str],
        target_vocab_size: int,
        min_frequency: int = 2,
        max_token_bytes: int = DEFAULT_MAX_TOKEN_BYTES,
    ) -> "BytePairTokenizer":
        if target_vocab_size < self.vocab_size:
            raise ValueError("Tokenizer expansion cannot shrink or reassign the existing vocabulary")
        if min_frequency < 2 or max_token_bytes < 2:
            raise ValueError("min_frequency must be at least 2 and max_token_bytes at least 2")
        materialized = list(texts)
        if not materialized:
            raise ValueError("Tokenizer expansion requires at least one text record")
        if any(not isinstance(text, str) for text in materialized):
            raise TypeError("Tokenizer expansion records must be strings")
        sequences = [self.encode(text) for text in materialized]
        return self._learn_merges(sequences, target_vocab_size, min_frequency, max_token_bytes)

    def encode(self, text: str, add_bos: bool = False, add_eos: bool = False) -> list[int]:
        if not isinstance(text, str):
            raise TypeError("encode expects a string")
        sequence = list(text.encode("utf-8", errors="strict"))
        for left, right, new_id in self._merges:
            sequence = self._merge_pair(sequence, (left, right), new_id)
        if add_bos:
            sequence.insert(0, self._special_ids["<bos>"])
        if add_eos:
            sequence.append(self._special_ids["<eos>"])
        return sequence

    def decode(
        self,
        token_ids: Sequence[int],
        skip_special_tokens: bool = False,
        errors: str = "strict",
    ) -> str:
        if errors not in {"strict", "replace", "ignore", "backslashreplace"}:
            raise ValueError("Unsupported UTF-8 decoding error mode")
        special_by_id = {value: key for key, value in self._special_ids.items()}
        byte_buffer = bytearray()
        output: list[str] = []
        for token_id in token_ids:
            if not isinstance(token_id, int) or token_id < 0 or token_id >= self.vocab_size:
                raise ValueError(f"Invalid token ID: {token_id!r}")
            if token_id in special_by_id:
                if byte_buffer:
                    output.append(byte_buffer.decode("utf-8", errors=errors))
                    byte_buffer.clear()
                if not skip_special_tokens:
                    output.append(special_by_id[token_id])
            else:
                byte_buffer.extend(self._bytes_for_token(token_id))
        if byte_buffer:
            output.append(byte_buffer.decode("utf-8", errors=errors))
        return "".join(output)

    def inspect_text(self, text: str) -> dict[str, object]:
        categories: Counter[str] = Counter(unicodedata.category(char)[0] for char in text)
        return {
            "unicode_data_version": self.unicode_data_version,
            "codepoints": len(text),
            "utf8_bytes": len(text.encode("utf-8", errors="strict")),
            "unicode_categories": dict(sorted(categories.items())),
        }

    @staticmethod
    def _unicode_kind(char: str) -> str:
        category = unicodedata.category(char)
        if char.isspace():
            return "whitespace"
        if category.startswith("L"):
            return "letter"
        if category.startswith("M"):
            return "mark"
        if category.startswith("N"):
            return "number"
        if category.startswith("P"):
            return "punctuation"
        if category.startswith("S"):
            return "symbol"
        if category.startswith("C"):
            return "control_or_format"
        return "other"

    def segment(self, text: str) -> list[dict[str, object]]:
        """Split into lossless Unicode-category runs without normalizing input."""
        if not isinstance(text, str):
            raise TypeError("segment expects a string")
        if not text:
            return []
        segments: list[dict[str, object]] = []
        start = 0
        byte_start = 0
        current_kind = self._unicode_kind(text[0])
        for index in range(1, len(text) + 1):
            next_kind = self._unicode_kind(text[index]) if index < len(text) else None
            if next_kind != current_kind:
                value = text[start:index]
                byte_end = byte_start + len(value.encode("utf-8", errors="strict"))
                segments.append({
                    "kind": current_kind,
                    "text": value,
                    "char_start": start,
                    "char_end": index,
                    "byte_start": byte_start,
                    "byte_end": byte_end,
                    "token_ids": self.encode(value),
                })
                byte_start = byte_end
                start = index
                current_kind = next_kind
        return segments

    def encode_segments(self, text: str) -> list[dict[str, object]]:
        """Return categorized segments with BPE IDs; concatenation is exactly reversible."""
        return self.segment(text)

    def coverage_report(self, text: str) -> dict[str, object]:
        """Report Unicode categories and observed character-name prefixes."""
        if not isinstance(text, str):
            raise TypeError("coverage_report expects a string")
        scripts: Counter[str] = Counter()
        categories: Counter[str] = Counter()
        for char in text:
            name = unicodedata.name(char, "UNNAMED")
            prefix = name.split(" ", 1)[0] if name != "UNNAMED" else "UNNAMED"
            scripts[prefix] += 1
            categories[unicodedata.category(char)] += 1
        encoded = self.encode(text)
        return {
            "unicode_data_version": self.unicode_data_version,
            "characters": len(text),
            "utf8_bytes": len(text.encode("utf-8", errors="strict")),
            "token_count": len(encoded),
            "unicode_categories": dict(sorted(categories.items())),
            "unicode_name_prefixes": dict(sorted(scripts.items())),
            "round_trip_exact": self.decode(encoded) == text,
        }

    def iter_vocabulary(self) -> Iterator[dict[str, object]]:
        special_by_id = {value: key for key, value in self._special_ids.items()}
        for token_id, token_bytes in enumerate(self._token_bytes):
            if token_id in special_by_id:
                yield {"id": token_id, "kind": "special", "token": special_by_id[token_id]}
            else:
                if token_bytes is None:
                    raise ValueError(f"Unmapped vocabulary ID: {token_id}")
                yield {
                    "id": token_id,
                    "kind": "byte" if token_id < self.BASE_VOCAB_SIZE else "merge",
                    "bytes_base64": base64.b64encode(token_bytes).decode("ascii"),
                    "preview": token_bytes.decode("utf-8", errors="replace"),
                }

    def save(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "format_version": self.FORMAT_VERSION,
            "vocab_size": self.vocab_size,
            "special_tokens": list(self.SPECIAL_TOKENS),
            "special_token_ids": self._special_ids,
            "tokens_base64": [
                None if token is None else base64.b64encode(token).decode("ascii")
                for token in self._token_bytes
            ],
            "merges": [list(merge) for merge in self._merges],
            "merge_frequencies": self._merge_frequencies,
            "unicode_data_version": self.unicode_data_version,
            "encoding": "UTF-8 byte-level BPE; no normalization",
            "fingerprint": self.fingerprint(),
        }
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        temporary.replace(destination)

    @classmethod
    def load(cls, path: str | Path) -> "BytePairTokenizer":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        version = data.get("format_version")
        if tuple(data.get("special_tokens", ())) != cls.SPECIAL_TOKENS:
            raise ValueError("Tokenizer special-token definitions are incompatible")
        tokenizer = cls()
        if version == 2:
            old_tokens = [base64.b64decode(item, validate=True) for item in data["tokens_base64"]]
            tokenizer._token_bytes = old_tokens + [None] * len(cls.SPECIAL_TOKENS)
            offset = len(old_tokens)
            tokenizer._special_ids = {token: offset + index for index, token in enumerate(cls.SPECIAL_TOKENS)}
            tokenizer._merges = [tuple(map(int, merge)) for merge in data["merges"]]
            tokenizer._merge_frequencies = [0] * len(tokenizer._merges)
        elif version == cls.FORMAT_VERSION:
            special_ids = {str(key): int(value) for key, value in data["special_token_ids"].items()}
            if set(special_ids) != set(cls.SPECIAL_TOKENS) or len(set(special_ids.values())) != len(special_ids):
                raise ValueError("Invalid special-token ID mapping")
            tokenizer._token_bytes = [
                None if item is None else base64.b64decode(item, validate=True)
                for item in data["tokens_base64"]
            ]
            tokenizer._special_ids = special_ids
            tokenizer._merges = [tuple(map(int, merge)) for merge in data["merges"]]
            tokenizer._merge_frequencies = [int(value) for value in data.get("merge_frequencies", [])]
            if not tokenizer._merge_frequencies:
                tokenizer._merge_frequencies = [0] * len(tokenizer._merges)
        else:
            raise ValueError(f"Unsupported tokenizer format version: {version}")

        if tokenizer.vocab_size != int(data["vocab_size"]):
            raise ValueError("Tokenizer vocabulary size does not match serialized tokens")
        special_ids_set = set(tokenizer._special_ids.values())
        if any(i < cls.BASE_VOCAB_SIZE or i >= tokenizer.vocab_size for i in special_ids_set):
            raise ValueError("Special-token ID is outside the vocabulary")
        for token_id, token in enumerate(tokenizer._token_bytes):
            if (token_id in special_ids_set) != (token is None):
                raise ValueError("Tokenizer contains an unmapped or conflicting token ID")
        if len(tokenizer._merge_frequencies) != len(tokenizer._merges):
            raise ValueError("Merge frequency metadata is inconsistent")
        for left, right, new_id in tokenizer._merges:
            if left >= new_id or right >= new_id or new_id >= tokenizer.vocab_size:
                raise ValueError("Tokenizer merge table is invalid")
            if left in special_ids_set or right in special_ids_set or new_id in special_ids_set:
                raise ValueError("Special tokens cannot participate in BPE merge rules")
            if tokenizer._token_bytes[new_id] != tokenizer._bytes_for_token(left) + tokenizer._bytes_for_token(right):
                raise ValueError("Tokenizer merge payload is inconsistent")
        saved_fingerprint = data.get("fingerprint")
        if version == cls.FORMAT_VERSION and saved_fingerprint and saved_fingerprint != tokenizer.fingerprint():
            raise ValueError("Tokenizer fingerprint does not match its vocabulary payload")
        return tokenizer
