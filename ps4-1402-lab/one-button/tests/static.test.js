import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const read = (name) => readFileSync(join(root, name), "utf8");
const version = "1.7.0";

test("all release version markers are aligned", () => {
  assert.match(read("index.html"), new RegExp("v" + version));
  assert.match(read("main.js"), new RegExp('version: "' + version + '"'));
  assert.match(read("package.json"), new RegExp('"version": "' + version + '"'));
  assert.match(read("README.md"), new RegExp("v" + version));
  assert.match(read("cache.appcache"), new RegExp("v" + version));
  assert.match(read("sw.js"), /host-v11/);
  assert.match(read("main.js"), /host-v11/);
});

test("safe probe contains functional browser checks", () => {
  const probe = read("probe.js");
  assert.match(probe, /async function run/);
  assert.match(probe, /testIndexedDB/);
  assert.match(probe, /testCacheStorage/);
  assert.match(probe, /testWebCryptoDigest/);
  assert.match(probe, /loseContext/);
  assert.match(read("main.js"), /await window\.JBhereSafeProbe\.run\(\)/);
});

test("reports explicitly exclude exploit execution", () => {
  assert.match(read("probe.js"), /Sem CVE proof/);
  assert.match(read("index.html"), /não é um HEN nem um jailbreak/i);
  assert.match(read("README.md"), /does not activate HEN/i);
});

test("private report reads require a bearer header", () => {
  const api = read("api/metadata.js");
  assert.match(api, /sameSecret\(bearer, expected\)/);
  assert.doesNotMatch(api, /searchParams\.get\(["']key["']\)/);
  assert.match(read("README.md"), /Query-string tokens are not accepted/);
});

test("evidence does not claim a verified complete 14.02 jailbreak", () => {
  const evidence = JSON.parse(read("evidence.json"));
  assert.equal(evidence.firmware14_02.publicChain, "NO_PUBLIC_REPRODUCIBLE_FULL_JAILBREAK_VERIFIED");
  assert.equal(evidence.firmware14_02.experimentalKernelClaim.independentReproduction, false);
});
