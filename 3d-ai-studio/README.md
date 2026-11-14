# 3D AI Studio — Sandbox-trained Alpha

Mobile-first 3D scene editor. The Android app is generated with Capacitor and built through GitHub Actions.

## App features in this branch

- Three.js real-time viewport with object selection, transforms and material color editing.
- Scene generation driven by a compact neural classifier trained from random initialization in the isolated training sandbox.
- Six learned scene intents: forest, city, character, vehicle, interior and abstract.
- Procedural geometry assembly with boxes, spheres, capsules, cylinders, cones and toruses.
- Simple and advanced procedural motion previews: idle, orbit, walk, run, jump and combo.
- JSON project import/export and binary GLB export.
- Simplified three-area interface: Scene, AI Creator and Animation.

## Isolated sandbox

The `training-sandbox/` directory is outside this app directory. It generates OBJ examples, UV coordinates, face normals, material files, PPM texture maps, mesh inspection metadata, animation clips and multilingual training examples. It trains a small MLP from random weights and validates it on held-out prompts.

The APK build receives only `scene-brain.json`, the compact trained checkpoint. The sandbox source, dataset, OBJ examples, textures, reports and training scripts are not copied into the app bundle.

Run the sandbox independently:

```bash
node training-sandbox/train.mjs
```

The GitHub Actions workflow runs this training and validation job before typecheck, tests, web build and Android APK packaging. A sandbox artifact is uploaded separately from the APK artifact.

## Model limits

This is a small supervised classifier, not a large language model. It learns to map synthetic multilingual descriptions to six scene categories; geometry is assembled by procedural rules. It does not yet understand arbitrary 3D code, create production topology from free-form descriptions, or learn from external image/video datasets. The sandbox is a reproducible training job, not a permanently running cloud process.
