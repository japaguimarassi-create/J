import argparse
import gzip
import json
from pathlib import Path

from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers

from tokenizer import normalize_text


SPECIAL_TOKENS = ["[PAD]", "[BOS]", "[EOS]", "[UNK]"]


def iter_training_text(path):
    source = Path(path)
    opener = gzip.open if str(source).endswith(".gz") else open
    with opener(source, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            text = row.get("text")
            if isinstance(text, str) and text.strip():
                yield normalize_text(text)


def train_bpe(corpus_path, output_path, vocab_size=32768, min_frequency=2):
    if vocab_size < 260:
        raise ValueError("BPE vocab_size must be at least 260 to reserve all byte values and four special tokens.")
    if min_frequency < 1:
        raise ValueError("min_frequency must be positive.")

    tokenizer = Tokenizer(models.BPE(unk_token="[UNK]"))
    tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tokenizer.decoder = decoders.ByteLevel()
    trainer = trainers.BpeTrainer(
        vocab_size=vocab_size,
        min_frequency=min_frequency,
        special_tokens=SPECIAL_TOKENS,
        initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),
        show_progress=True,
    )
    tokenizer.train_from_iterator(iter_training_text(corpus_path), trainer=trainer)
    actual_vocab_size = tokenizer.get_vocab_size(with_added_tokens=True)
    if actual_vocab_size < 260:
        raise RuntimeError(f"Tokenizer learned an unexpectedly small vocabulary: {actual_vocab_size}")

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    tokenizer.save(str(destination))
    return {
        "tokenizer": str(destination),
        "requested_vocab_size": vocab_size,
        "actual_vocab_size": actual_vocab_size,
        "minimum_byte_level_vocab": 260,
        "special_token_ids": {
            token: tokenizer.token_to_id(token) for token in SPECIAL_TOKENS
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("artifacts/tokenizer.json"))
    parser.add_argument("--vocab-size", type=int, default=32768)
    parser.add_argument("--min-frequency", type=int, default=2)
    args = parser.parse_args()
    print(json.dumps(
        train_bpe(args.data, args.output, args.vocab_size, args.min_frequency),
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
