"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const root = path.join(__dirname, "..");
const html = fs.readFileSync(path.join(root, "index.html"), "utf8");
const main = fs.readFileSync(path.join(root, "main.js"), "utf8");
const evidence = JSON.parse(fs.readFileSync(path.join(root, "evidence.json"), "utf8"));

test("page contains exactly one button", () => {
  assert.equal((html.match(/<button\b/gi) || []).length, 1);
});
test("page contains no forms or external links", () => {
  assert.equal((html.match(/<form\b/gi) || []).length, 0);
  assert.equal((html.match(/<a\b/gi) || []).length, 0);
});
test("one-button flow has offline cache and resume behavior", () => {
  assert.match(main, /serviceWorker/);
  assert.match(main, /jbhereps4:prepared/);
  assert.match(main, /window\.addEventListener\("load"/);
});
test("14.02 gate stays closed until independently verified", () => {
  assert.equal(evidence.firmware14_02.publicChain, "NOT_VERIFIED");
  assert.equal(evidence.firmware14_02.reproducibleHardwareTest, false);
  assert.equal(evidence.goldhen.firmware14_02Listed, false);
  assert.equal(evidence.safety.exploitCodeIncluded, false);
});
test("diagnostics explicitly avoid exploitation", () => {
  assert.match(main, /exploitExecuted: false/);
  assert.match(main, /kernelAccess: false/);
  assert.match(main, /firmwareModified: false/);
});