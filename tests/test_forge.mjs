import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { DEFAULT_SOURCE, parseForge, sampleObject, findSceneDuration, upsertKeyframe } from "../web/forge.mjs";

test("parses the default project and its four objects", () => {
  const project = parseForge(DEFAULT_SOURCE);
  assert.equal(project.errors.length, 0, JSON.stringify(project.errors));
  assert.equal(project.name, "Orbit Study");
  assert.equal(project.objects.length, 4);
  assert.equal(project.fps, 24);
});

test("interpolates numerical keyframes", () => {
  const project = parseForge('scene "Move" fps=24 width=960 height=540\ncircle orb x=0 y=0 radius=10 color=#65e8d4\nkey orb at=0 x=0 y=10\nkey orb at=20 x=100 y=50');
  const middle = sampleObject(project.objects[0], 10);
  assert.equal(middle.x, 50);
  assert.equal(middle.y, 30);
});

test("rejects unsupported commands and duplicate names", () => {
  const project = parseForge('scene "Bad"\ncircle orb x=0 y=0 radius=10 color=#65e8d4\ncircle orb x=0 y=0 radius=10 color=#65e8d4\nrun javascript=bad');
  assert.ok(project.errors.some((error) => error.message.includes("já existe")));
  assert.ok(project.errors.some((error) => error.message.includes("desconhecido")));
});

test("reports unknown keyframe targets", () => {
  const project = parseForge('scene "Bad"\ncircle orb x=0 y=0 radius=10 color=#65e8d4\nkey nope at=4 x=2');
  assert.ok(project.errors.some((error) => error.message.includes("não declarado")));
});

test("finds timeline duration from the highest frame", () => {
  assert.equal(findSceneDuration(parseForge(DEFAULT_SOURCE)), 48);
  const project = parseForge('scene "Long"\ncircle orb x=0 y=0 radius=10 color=#65e8d4\nkey orb at=120 x=30');
  assert.equal(findSceneDuration(project), 120);
});

test("upserts a keyframe without duplication", () => {
  const before = 'scene "Move"\ncircle orb x=0 y=0 radius=10 color=#65e8d4\nkey orb at=2 x=1';
  const after = upsertKeyframe(before, "key", "orb", 2, { x: 10, y: 20 });
  assert.equal((after.match(/key orb at=2/g) || []).length, 1);
  assert.match(after, /key orb at=2 x=10 y=20/);
});

test("every FORGE code sample in the training corpus parses without errors", async () => {
  const text = await readFile(new URL("../data/seed.jsonl", import.meta.url), "utf8");
  for (const line of text.split(/\r?\n/).filter(Boolean)) {
    const example = JSON.parse(line);
    const snippets = [...example.response.matchAll(/~~~forge\s*\n([\s\S]*?)\n~~~/g)];
    for (const snippet of snippets) {
      const project = parseForge(snippet[1]);
      assert.equal(project.errors.length, 0, example.prompt + ": " + JSON.stringify(project.errors));
    }
  }
});
