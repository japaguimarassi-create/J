import test from "node:test";
import assert from "node:assert/strict";
import { parseForge, inspectForge } from "../app/forge.js";

const valid2d = [
  'project "Test"',
  'scene "Moving ball" mode 2d fps 30 duration 3',
  'object "Ball" circle color "#58d6ff" at (48,130,0) size (38,38)',
  'animate "Ball" move from (48,130,0) to (330,130,0) from 0s to 3s ease smooth',
].join("\n");

test("parses valid 2D script and keyframes", () => {
  const scene = parseForge(valid2d);
  assert.equal(scene.mode, "2d");
  assert.equal(scene.duration, 3);
  assert.equal(scene.objects.length, 1);
  assert.equal(scene.animations[0].property, "move");
});

test("parses a 3D torus", () => {
  const scene = parseForge('scene "Ring" mode 3d fps 60 duration 4\nobject "Aro" torus color "#9b8cff" at (0,0,0) scale (1,1,1)');
  assert.equal(scene.objects[0].type, "torus");
});

test("rejects duplicate object names", () => {
  assert.throws(() => parseForge('scene "Bad" mode 2d fps 30 duration 2\nobject "B" circle color "#ffffff" at (0,0,0) size (10,10)\nobject "B" box color "#ffffff" at (0,0,0) size (10,10)'), /duplicado/);
});

test("rejects animation reference to a missing object", () => {
  assert.throws(() => parseForge('scene "Bad" mode 2d fps 30 duration 2\nobject "B" circle color "#ffffff" at (0,0,0) size (10,10)\nanimate "Missing" move from (0,0,0) to (1,1,1) from 0s to 1s ease linear'), /não existe/);
});

test("rejects animations beyond scene duration", () => {
  assert.throws(() => parseForge('scene "Bad" mode 2d fps 30 duration 2\nobject "B" circle color "#ffffff" at (0,0,0) size (10,10)\nanimate "B" move from (0,0,0) to (1,1,1) from 0s to 3s ease linear'), /depois da duração/);
});

test("rejects multiple scene declarations", () => {
  assert.throws(() => parseForge('scene "One" mode 2d fps 30 duration 2\nscene "Two" mode 2d fps 30 duration 2\nobject "B" circle color "#ffffff" at (0,0,0) size (10,10)'), /apenas uma cena/);
});

test("rejects malformed decimals", () => {
  assert.throws(() => parseForge('scene "Bad" mode 2d fps 30 duration 1..2\nobject "B" circle color "#ffffff" at (0,0,0) size (10,10)'), /sintaxe FORGE desconhecida/);
});

test("reports readable parser errors", () => {
  const result = inspectForge("not a forge statement");
  assert.equal(result.ok, false);
  assert.match(result.error, /Linha 1/);
});
