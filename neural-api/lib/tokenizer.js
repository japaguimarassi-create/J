"use strict";

const VOCABULARY_SIZE = 16000;
const TOKEN_PATTERN = /[\\p{L}\\p{M}\\p{N}_]+|[^\\s\\p{L}\\p{M}\\p{N}_]/gu;

function stableTokenId(token) {
  let hash = 2166136261;
  for (let i = 0; i < token.length; i += 1) {
    hash ^= token.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0) % VOCABULARY_SIZE;
}

function tokenize(text) {
  const normalized = String(text || "").normalize("NFC");
  const tokens = normalized.match(TOKEN_PATTERN) || [];
  return {
    tokenizer: "neural-procedural-tokenizer-0.1",
    mode: "deterministic-lexical-baseline",
    trained_bpe_merges_loaded: false,
    vocabulary_size: VOCABULARY_SIZE,
    tokens,
    token_ids: tokens.map(stableTokenId),
    total_tokens: tokens.length
  };
}

module.exports = { tokenize, stableTokenId, VOCABULARY_SIZE };