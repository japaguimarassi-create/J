"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const read = (name) => fs.readFileSync(path.join(root, name), "utf8");
const json = (name) => JSON.parse(read(name));

test("health endpoint identifies the read-only 14.02 project", () => {
  const health = json("health.json");
  assert.equal(health.firmware, "14.02");
  assert.equal(health.status, "ok");
  assert.equal(health.exploitExecution, false);
  assert.equal(health.version, "1.3.0");
});

test("evidence registry does not claim a verified public chain", () => {
  const evidence = json("evidence.json");
  assert.equal(evidence.targetFirmware, "14.02");
  assert.equal(evidence.status, "NO_PUBLIC_CHAIN_INDEPENDENTLY_VERIFIED");
  assert.ok(Array.isArray(evidence.findings) && evidence.findings.length >= 3);
  assert.ok(Array.isArray(evidence.sources) && evidence.sources.length >= 3);
  for (const source of evidence.sources) {
    assert.match(source.url, /^https:\/\//);
  }
});

test("web app exposes real diagnostics and honest report fields", () => {
  const html = read("index.html");
  for (const id of ["run", "stop", "results", "log", "md", "json", "firmware"]) {
    assert.ok(html.includes('id="' + id + '"'), "missing UI control: " + id);
  }
  assert.match(html, /exploitExecuted:false/);
  assert.match(html, /kernelModified:false/);
  assert.match(html, /nenhum exploit foi executado/i);
  assert.match(html, /async function retry/);
  assert.match(html, /value="60">60 tentativas \(máximo\)<\/option>/);
  assert.match(html, /Math\.min\(250\*i,2000\)/);
  assert.match(html, /scope:"browser-api-only"/);
  assert.match(html, /kernelProbe:"not-performed"/);
  assert.match(html, /Kernel \/ syscall fora do navegador/);
  assert.match(html, /SharedArrayBuffer \/ Atomics/);
  assert.match(html, /N\/A/);
});

test("offline worker is same-origin and GET-only", () => {
  const sw = read("sw.js");
  assert.match(sw, /request\.method!=="GET"/);
  assert.match(sw, /url\.origin!==self\.location\.origin/);
  assert.match(sw, /caches\.open/);
  assert.match(sw, /ps4-1402-lab-v1\.3\.0/);
});

test("manifest and Vercel headers are valid JSON", () => {
  const manifest = json("manifest.webmanifest");
  assert.equal(manifest.name, "PS4 14.02 Research Lab");
  const vercel = json("vercel.json");
  assert.ok(Array.isArray(vercel.headers));
  assert.ok(vercel.headers.some((entry) => entry.source === "/(.*)"));
});

test("required static assets exist", () => {
  for (const name of ["index.html", "manifest.webmanifest", "sw.js", "health.json", "evidence.json", "vercel.json"]) {
    assert.ok(fs.statSync(path.join(root, name)).isFile(), name + " missing");
  }
});
