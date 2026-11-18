from __future__ import annotations
import json
from collections import Counter
from pathlib import Path
from typing import Iterable

class ByteBPE:
    FORMAT_VERSION = 1

    def __init__(self, merges: list[tuple[bytes, bytes]] | None = None):
        self.merges = merges or []
        self.ranks = {pair: rank for rank, pair in enumerate(self.merges)}
        self.vocab = {bytes([i]): i for i in range(256)}
        for left, right in self.merges:
            token = left + right
            if token not in self.vocab:
                self.vocab[token] = len(self.vocab)
        self.inverse_vocab = {v: k for k, v in self.vocab.items()}

    @staticmethod
    def _pairs(tokens: list[bytes]):
        return set(zip(tokens, tokens[1:]))

    @classmethod
    def train(cls, texts: Iterable[str], vocab_size: int = 512):
        if vocab_size < 256:
            raise ValueError("vocab_size must be at least 256")
        sequences = [[bytes([b]) for b in text.encode("utf-8")] for text in texts]
        merges: list[tuple[bytes, bytes]] = []
        while 256 + len(merges) < vocab_size:
            counts = Counter()
            for seq in sequences:
                counts.update(zip(seq, seq[1:]))
            if not counts:
                break
            pair, frequency = counts.most_common(1)[0]
            if frequency < 2:
                break
            merges.append(pair)
            updated = []
            for seq in sequences:
                out, i = [], 0
                while i < len(seq):
                    if i + 1 < len(seq) and (seq[i], seq[i + 1]) == pair:
                        out.append(seq[i] + seq[i + 1])
                        i += 2
                    else:
                        out.append(seq[i])
                        i += 1
                updated.append(out)
            sequences = updated
        return cls(merges)

    def encode(self, text: str):
        tokens = [bytes([b]) for b in text.encode("utf-8")]
        while len(tokens) > 1:
            candidates = [(self.ranks[p], p) for p in self._pairs(tokens) if p in self.ranks]
            if not candidates:
                break
            _, chosen = min(candidates, key=lambda item: item[0])
            merged, i = [], 0
            while i < len(tokens):
                if i + 1 < len(tokens) and (tokens[i], tokens[i + 1]) == chosen:
                    merged.append(tokens[i] + tokens[i + 1])
                    i += 2
                else:
                    merged.append(tokens[i])
                    i += 1
            tokens = merged
        return [self.vocab[token] for token in tokens]

    def decode(self, ids: Iterable[int]):
        return b"".join(self.inverse_vocab[int(i)] for i in ids).decode("utf-8", errors="strict")

    def save(self, path: str | Path):
        payload = {"format_version": self.FORMAT_VERSION, "merges": [[a.hex(), b.hex()] for a, b in self.merges]}
        Path(path).write_text(json.dumps(payload), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path):
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if payload.get("format_version") != cls.FORMAT_VERSION:
            raise ValueError("Unsupported tokenizer format version")
        return cls([(bytes.fromhex(a), bytes.fromhex(b)) for a, b in payload["merges"]])
