# MotionForge Generation Studio

This package adds three output paths to MotionForge:

1. **Images and drawings:** SDXL text-to-image and image-to-image through Hugging Face Diffusers, optionally with a locally trained LoRA adapter.
2. **Video:** LTX-2.5 workflows executed by a local ComfyUI server using its API format. Supports text-to-video, image-to-video and additional controls implemented by the selected workflow.
3. **3D assets:** Tencent Hunyuan3D-2.1 image-to-mesh, with optional PBR texture generation.

These are integrations with pretrained foundation models, not claims that MotionForge trained new foundation models from scratch. The visual retrieval adapter and the SDXL LoRA have separate jobs: one learns to find references; the other adapts the image generator.

## Hardware reality

- **SDXL inference:** use a CUDA GPU. The low-VRAM option enables model CPU offload, but it is slower. CPU-only generation is not recommended.
- **SDXL LoRA training:** the included wrapper checks for CUDA and defaults to a 12 GB VRAM minimum. 16–24 GB or more is more comfortable; the exact memory need depends on resolution and settings.
- **LTX-2.5 video:** run through ComfyUI and use the official workflow for the selected checkpoint. Model access, memory, clip length, resolution and audio support depend on the specific LTX-2.5 model and workflow.
- **Hunyuan3D-2.1:** the upstream project reports approximately 10 GB VRAM for shape generation, 21 GB for texture generation and 29 GB for the combined shape-plus-texture path. This is not a phone workload.

The Moto G04S can open the editor, prepare prompts, manage files and connect to a remote host. It cannot realistically run these large generator weights directly.

## Run image generation from Android with Colab

Open the [MotionForge SDXL generation and training notebook](https://colab.research.google.com/github/japaguimarassi-create/J/blob/motionforge-multimodal-learning/generation/generate_colab.ipynb). It mounts Drive, checks for an available GPU, runs SDXL text-to-image/image-to-image and optionally prepares and trains a LoRA adapter. The notebook covers image generation; video and 3D require their separate runtimes described below.

## Install image generation

Use Python 3.10 or newer in a CUDA-enabled environment:

~~~bash
python -m pip install -r generation/requirements.txt
python -m pip install -r generation/api-requirements.txt
~~~

The first SDXL run downloads model weights from Hugging Face. A Hugging Face account may be required to accept model terms or authenticate depending on the checkpoint.

### Generate an image

~~~bash
python -m generation.image --prompt "Original anime character concept, detailed cel shading, dramatic cinematic rim light" --width 1024 --height 1024 --steps 30 --seed 20261113 --low-vram --output outputs/image.png
~~~

### Transform an image

~~~bash
python -m generation.image --prompt "Turn this rough sketch into a polished anime character design, preserve the pose and silhouette" --init-image sketch.png --strength 0.65 --low-vram --output outputs/painted.png
~~~

### Use a trained LoRA

~~~bash
python -m generation.image --prompt "A character in the learned visual style" --lora artifacts/generation/sdxl-lora --low-vram --output outputs/lora-image.png
~~~

SDXL is distributed under the CreativeML Open RAIL++-M license. Read the complete license, especially its use-based restrictions, before use or distribution: https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0

## Train the image generator with licensed references

The current SDXL LoRA route trains an adapter rather than updating and redistributing all SDXL base weights.

First, prepare the visual pairs. The preparation step copies only CC0 1.0 and CC BY 4.0 files, checks that the image opens, deduplicates by SHA-256, and writes a Hugging Face imagefolder metadata file with attribution fields.

~~~bash
python -m generation.prepare_sdxl_dataset --pairs datasets/pairs.jsonl --output datasets/sdxl_lora --max-items 5000 --max-total-gb 20
~~~

Install the current Diffusers source and its training dependencies. The upstream SDXL LoRA training script is maintained in the Diffusers repository; its current development script may require a recent development version of Diffusers.

~~~bash
git clone --depth 1 https://github.com/huggingface/diffusers.git third_party/diffusers
python -m pip install -e third_party/diffusers
python -m pip install -r generation/training-requirements.txt
~~~

Start a bounded training run:

~~~bash
python -m generation.train_sdxl_lora --dataset-dir datasets/sdxl_lora --diffusers-root third_party/diffusers --steps 2000 --checkpoint-every 250 --batch-size 1 --gradient-accumulation 4 --rank 16 --use-8bit-adam
~~~

Resume from the most recent training checkpoint:

~~~bash
python -m generation.train_sdxl_lora --dataset-dir datasets/sdxl_lora --diffusers-root third_party/diffusers --steps 4000 --resume --use-8bit-adam
~~~

The saved LoRA is written to artifacts/generation/sdxl-lora/. Keep the original dataset manifest, license information and training configuration with the resulting adapter. Do not use content with unclear rights or captions copied from unverified sources.

## Video generation with LTX-2.5 and ComfyUI

LTX-2.5 is the latest LTX model announced on August 11, 2026. It supports multi-shot generation and synchronized audio/video. The current upstream LTX-Video repository directs new projects to the separate LTX-2 repository. Code and weights have different license terms; the weights are distributed under an LTX-2.x Community License and may require gated access.

- Official code: https://github.com/Lightricks/LTX-2
- Model overview: https://ltx.io/model/ltx-2-5
- Official documentation: https://docs.ltx.io/models/ltx-2-5
- ComfyUI: https://www.comfy.org/

Install ComfyUI and the official LTX nodes/workflow required by the checkpoint you have accepted access to. Export the workflow in API format and place the JSON file inside generation/workflows/. The node IDs and input names depend on the selected workflow.

~~~bash
python -m generation.video_comfy --comfy-url http://127.0.0.1:8188 --workflow generation/workflows/ltx25-api.json --prompt-text "A cinematic anime hero turns toward the camera as wind moves their coat" --prompt-node 6 --prompt-input text --output-dir outputs/video
~~~

For image-to-video, add the initial image and the workflow node that accepts it:

~~~bash
python -m generation.video_comfy --comfy-url http://127.0.0.1:8188 --workflow generation/workflows/ltx25-api.json --prompt-text "The character slowly turns, hair and fabric moving naturally" --prompt-node 6 --image first-frame.png --image-node 12 --image-input image --output-dir outputs/video
~~~

Node IDs in the example are placeholders; inspect your exported API workflow and replace them. Other workflow inputs can be adjusted using repeatable assignments:

~~~bash
--set 6.text="Your prompt" --set 9.width=768 --set 9.height=512
~~~

Never expose an unauthenticated ComfyUI port to the public internet. Keep it on loopback or behind authenticated HTTPS.

## 3D generation with Hunyuan3D-2.1

The upstream project publishes an image-to-shape pipeline and a separate PBR texturing pipeline. Follow its installation instructions, including the required CUDA/PyTorch version and mesh renderer compilation steps:

https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1

Clone the upstream repository outside MotionForge's Git-tracked files:

~~~bash
git clone --depth 1 https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1.git third_party/Hunyuan3D-2.1
~~~

Generate a shape:

~~~bash
python -m generation.model3d --image outputs/image.png --output outputs/3d/character.glb
~~~

Generate and texture a shape:

~~~bash
python -m generation.model3d --image outputs/image.png --texture --paint-views 6 --paint-resolution 512 --output outputs/3d/character-textured.glb
~~~

**License boundary:** Hunyuan3D-2.1 uses the Tencent Hunyuan 3D 2.1 Community License, not Apache-2.0. Read the Territory definition and Acceptable Use Policy before running it. The license explicitly prohibits using its model outputs/results to improve another AI model. For that reason, the generated 3D files are kept out of MotionForge's training dataset and must not be fed into the visual learner or the SDXL LoRA trainer.

## Start the local API

Start the MotionForge editor server in one terminal:

~~~bash
python server.py
~~~

Start the generator API in another terminal:

~~~bash
python -m generation.api
~~~

Open the generator page at:

~~~text
http://127.0.0.1:8000/generator.html
~~~

The API is bound to 127.0.0.1:8189 by default. To bind beyond loopback, set MOTIONFORGE_GENERATION_HOST and provide MOTIONFORGE_GENERATION_KEY; use HTTPS, firewall rules and authentication. Do not expose a public unauthenticated generation or ComfyUI service.

API health check:

~~~bash
curl http://127.0.0.1:8189/health
~~~

Generated media is written beneath outputs/. These files and model weights are ignored by Git. The UI does not upload generated media back to the training corpus.

## Storage policy

The Git branch contains source code, model registries, workflows documentation and training configurations. It deliberately excludes:

- base model weights;
- LoRA/checkpoint files;
- downloaded images, video clips and 3D assets;
- generated images, videos and meshes;
- API keys and private tokens.

Store large datasets and model outputs in local disk or external storage such as Google Drive. Save manifests and attribution records alongside them.
