# Unicode and tokenizer coverage

The tokenizer's 256 byte IDs are a complete fallback for valid UTF-8. They encode all Unicode scalar values, not merely a manually maintained language list. This includes current and previously unseen writing systems, combining marks, right-to-left text, full-width forms, emoji sequences, symbols, punctuation, brackets, mathematical operators, programming delimiters, whitespace and control/format characters.

No Unicode normalization is applied. This preserves exact source text and means visually equivalent strings with different codepoint sequences remain distinct. The Unicode database version used for inspection is recorded with the tokenizer artifact.

`segment(text)` groups contiguous Unicode general categories (letters, marks, numbers, punctuation, symbols, whitespace and control/format characters) and returns character offsets, UTF-8 byte offsets and BPE IDs. `coverage_report(text)` reports the actual categories and Unicode-name prefixes in a sample. These methods are for transparent inspection; the model still consumes the ordinary BPE token sequence.

Universal encoding coverage is not universal language understanding. Model quality for each language depends on the amount, quality, balance and licensing of training data and on multilingual evaluation.

# Periodic neural growth

`GrowthPolicy` proposes a larger model only after a configured training-step interval and a validation-loss gate. It can add Transformer depth, increase feed-forward width and enlarge context, subject to a hard parameter budget. It does not mutate a live model or overwrite a checkpoint. The caller must create a new version using the existing `--expand-from` training path, evaluate it, and promote it only after the release gates pass.

Tokenizer, model and application source remain separately versioned. Application-code changes are reviewed and tested through Git commits and CI; model training never edits its own source code or security policy.
