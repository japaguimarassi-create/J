"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { tokenize } = require("../lib/tokenizer");
const {
  ARCHITECTURE,
  latestUserMessage,
  detectIntent,
  generateProceduralReply,
  runBootstrap
} = require("../lib/procedural-engine");

test("target architecture declares at least 60,000 units", () => {
  assert.equal(ARCHITECTURE.targetUnits, 61440);
  assert.ok(ARCHITECTURE.targetUnits >= 60000);
});

test("tokenizer is deterministic for Brazilian Portuguese", () => {
  const first = tokenize("Olá, aldeão!");
  const second = tokenize("Olá, aldeão!");
  assert.deepEqual(first, second);
  assert.ok(first.total_tokens > 0);
});

test("latest user message ignores assistant messages", () => {
  assert.equal(
    latestUserMessage([
      { role: "user", content: "Oi" },
      { role: "assistant", content: "Olá" },
      { role: "user", content: "Como está a vila?" }
    ]),
    "Como está a vila?"
  );
});

test("intent detection identifies greetings", () => {
  assert.equal(detectIntent("Olá, tudo bem?"), "greeting");
});

test("procedural engine returns a Portuguese response and transparent telemetry", () => {
  const result = runBootstrap([{ role: "user", content: "Oi, aldeão!" }]);
  assert.match(result.content, /Olá/);
  assert.equal(result.telemetry.trained, false);
  assert.equal(result.telemetry.target_neurons, 61440);
});

test("general fallback discloses that weights are not trained", () => {
  const result = generateProceduralReply([
    { role: "user", content: "Explique a origem dos aldeões." }
  ]);
  assert.match(result.content, /pesos linguísticos treinados/);
});