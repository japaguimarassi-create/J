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
  assert.equal(health.version, "1.4.0");
});

test("evidence registry does not claim a verified public chain", () => {
  const evidence = json("evidence.json");
  assert.equal(evidence.targetFirmware, "14.02");
  assert.equal(evidence.status, "NO_PUBLIC_CHAIN_INDEPENDENTLY_VERIFIED");
  assert.ok(Array.isArray(evidence.findings) && evidence.findings.length >= 3);
  assert.ok(Array.isArray(evidence.sources) && evidence.sources.length >= 3);
  assert.ok(evidence.findings.some((x) => x.id === "prolapse-1402-diff"));
  assert.ok(evidence.findings.some((x) => x.id === "afterglow-1402-status"));
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
  assert.match(html, /O que mudou no 14\.02/);
  assert.match(html, /firmware-delta\.js/);
  assert.match(html, /AIO \/ Prolapse/);
  assert.match(html, /Afterglow \/ kernel/);
  assert.match(html, /BD-J \/ Blu-ray Java/);
  assert.match(html, /N\/A/);
});

test("offline worker is same-origin and GET-only", () => {
  const sw = read("sw.js");
  assert.match(sw, /request\.method!=="GET"/);
  assert.match(sw, /url\.origin!==self\.location\.origin/);
  assert.match(sw, /caches\.open/);
  assert.match(sw, /ps4-1402-lab-v1\.4\.0/);
  assert.match(sw, /firmware-delta\.json/);
  assert.match(sw, /firmware-delta\.js/);
});

test("manifest and Vercel headers are valid JSON", () => {
  const manifest = json("manifest.webmanifest");
  assert.equal(manifest.name, "PS4 14.02 Research Lab");
  const vercel = json("vercel.json");
  assert.ok(Array.isArray(vercel.headers));
  assert.ok(vercel.headers.some((entry) => entry.source === "/(.*)"));
});

test("required static assets exist", () => {
  for (const name of ["index.html", "manifest.webmanifest", "sw.js", "health.json", "evidence.json", "firmware-delta.json", "firmware-delta.js", "vercel.json"]) {
    assert.ok(fs.statSync(path.join(root, name)).isFile(), name + " missing");
  }
});

test("firmware delta data separates official notes from community findings", () => {
  const delta = json("firmware-delta.json");
  assert.equal(delta.comparison.from, "14.00");
  assert.equal(delta.comparison.to, "14.02");
  assert.equal(delta.version, "1.4.0");
  assert.ok(delta.officialTimeline.some((x) => x.firmware === "14.02"));
  assert.ok(delta.findings.some((x) => x.id === "prolapse"));
  assert.ok(delta.findings.some((x) => x.id === "afterglow"));
  assert.ok(delta.unknowns.length >= 3);
  assert.ok(delta.sources.every((x) => /^https:\/\//.test(x.url)));
});

test("browser scripts parse as JavaScript", () => {
  const html = read("index.html");
  const scriptStart = html.indexOf("<script>") + "<script>".length;
  const scriptEnd = html.indexOf("</script>", scriptStart);
  assert.ok(scriptStart >= "<script>".length && scriptEnd > scriptStart);
  new Function(html.slice(scriptStart, scriptEnd));
  new Function(read("firmware-delta.js"));
});
