# 3D AI Studio — isolated training sandbox

This folder is a development/training environment. It is deliberately outside `3d-ai-studio/`, so none of its scripts, datasets, OBJ meshes, textures or animation files are bundled into the Android APK.

## What it builds

- A small neural scene-intent classifier trained from random initialization using supervised backpropagation.
- Training examples across Portuguese, English, Spanish, Mandarin Chinese, Hindi and Arabic.
- OBJ learning examples: cube, pyramid, humanoid blockout, tree, house, car, crystal and ring.
- Mesh inspection metadata: vertices, polygon faces, topology, normal-generation note, UV recipe and material reference.
- Generated PPM texture maps and MTL material.
- Simple animation clips (idle, walk, run, jump) and advanced clips (combo, turn-and-react).
- A validation report and a compact JSON checkpoint for app inference.

## Run

```bash
node training-sandbox/train.mjs
```

Set `TRAIN_EPOCHS=300` to train longer. The sandbox has no external dataset dependency and is reproducible from its seed.

## Important boundary

This is a small model trained from scratch on synthetic teaching examples. It can learn the six scene categories represented in the dataset; it is not a large language model, does not learn every possible 3D concept, and cannot infer production-quality topology from arbitrary prompts. The generated checkpoint is a model artifact only. The sandbox, its datasets and its training code are never copied into the app or APK.
