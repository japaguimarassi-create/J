# Tokenizer coverage and expansion

## Representation guarantee

Klod's base alphabet is the 256 possible byte values. Input strings are encoded as UTF-8 bytes and then passed through ordered BPE merge rules. Consequently, every valid Unicode scalar value and every combination of such values can be represented, including text not present in the training corpus.

The tokenizer preserves:
- Latin, Cyrillic, Greek, Hebrew, Arabic, Indic and Southeast Asian writing systems.
- CJK ideographs, kana, hangul, Ethiopic, Armenian, Georgian, Khmer, Myanmar and other Unicode scripts.
- Accented and combining sequences without normalization.
- Bidirectional marks, zero-width joiners and variation selectors.
- Emoji sequences, skin-tone modifiers and flags.
- ASCII, full-width and script-specific punctuation.
- Slash and backslash, brackets, parentheses, braces, angle brackets and programming operators.
- Whitespace, line endings, tabs, null bytes and control characters representable in Python strings.

Punctuation is not discarded or treated as decoration. It is ordinary byte sequence content learned by the same BPE algorithm. For code, strings such as //, /* */, <=, !=, ===, ->, =>, ::, {}, (), [], / and backslash are all preserved exactly.

The Unicode Consortium's current release is Unicode 18.0.0 (September 16, 2026), listing 172,808 encoded characters. UTF-8 byte representation does not require the Python runtime's Unicode category database to know the name or script assignment of every code point. The inspect_text helper reports the Python runtime's Unicode database version so category reports are transparent.

**Important distinction:** representation coverage is not linguistic competence. The model still needs lawful, high-quality training examples for a language, its grammar, vocabulary, writing conventions and code ecosystem. No tokenizer can guarantee understanding of every language merely by assigning IDs to bytes.

## Version 3 ID layout

New tokenizers reserve IDs 0–255 for bytes and IDs 256–259 for PAD/BOS/EOS/UNK. BPE merges are appended after those reserved IDs. This keeps special-token IDs unchanged when the vocabulary grows.

The loader also reads format-v2 tokenizers. In those files the four special IDs were placed after the final merge. Their original IDs remain fixed during expansion, and newly learned merges are appended after them. The v3 serializer records the exact special-ID mapping and all token bytes, so migrated tokenizers remain reversible.

## Large vocabulary

The default target is 32,768 IDs. Larger targets such as 65,536 or 131,072 are configurable. A target is not a promise that the trainer will create that many entries: each new token requires a repeated adjacent pair meeting min_frequency. A short or repetitive corpus may stop early.

BPE training recomputes pair frequencies from the training sequences after each merge. This initial implementation prioritizes auditable correctness and determinism; very large corpora and vocabularies will need a separately benchmarked optimized pair-count engine before being used at scale.

## Periodic tokenizer growth

Use the saved tokenizer and append more merges:

    python -m klod.training.train --dataset data/new-corpus.jsonl --output-dir artifacts/v2 --tokenizer artifacts/v1/tokenizer.json --expand-tokenizer --expand-from artifacts/v1/checkpoints/latest.pt --vocab-size 65536 --steps 20000

The expansion procedure:
1. Loads the exact previous tokenizer.
2. Keeps every old token byte sequence, merge rule and special-token ID.
3. Encodes the new corpus using the old tokenizer.
4. Learns only new merges and assigns IDs after the existing vocabulary.
5. Saves a new tokenizer file in the new output directory.
6. Expands the neural output/input embedding to the new vocabulary and continues training.

Never delete the old tokenizer or checkpoint. Do not use --retrain-tokenizer when resuming or expanding an existing neural model.
