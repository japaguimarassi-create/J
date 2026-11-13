# MotionForge Multimodal Learning

This module extends the MotionForge branch with a reproducible pipeline for collecting, screening, preparing and learning from 2D images, rendered 3D objects and sampled video frames.

## What this creates

The visual learner is a real trainable retrieval model, not a claim that the existing 249,984-parameter ForgeStudent suddenly understands pixels. It uses a pretrained OpenCLIP visual/text encoder as a frozen feature extractor and learns small trainable projection heads over the approved local dataset. The resulting adapter learns to align descriptions with visual examples and supports text-to-asset search.

It is useful for learning visual vocabulary, composition references, object categories, motion references and finding relevant source assets inside MotionForge. It does not train a new diffusion model or produce original video/3D geometry by itself. The existing ForgeStudent remains a separate text/script model. This split is intentional: training a competitive image/video/3D generator from scratch on a phone is not realistic.

## Why the media is not committed to Git

Millions of media files would make the Git repository enormous, slow to clone and difficult to maintain. GitHub's branch stores code, source registry, manifests schema and instructions. Actual media stays in local storage or external dataset storage, and generated checkpoints stay in the ignored artifacts directory or a Drive bucket. The manifest records each asset's source, item-level license, attribution, URL, local path and SHA-256 digest.

The project does not claim to have downloaded millions of assets merely by creating this pipeline. Collection is opt-in, bounded by command-line limits, resumable and subject to the source's terms.

## Rights policy

Default training allowlist:

- CC0 1.0
- CC BY 4.0

The default policy excludes non-commercial, no-derivatives, share-alike and unknown licenses. Share-alike is excluded to avoid silently imposing obligations on the downstream model/data pipeline. Each record must carry item-level rights metadata and a source page. This is an engineering filter, not legal advice; verify rights for the intended use.

The registry in sources.json records the scale and limitations of candidate sources:

- Smithsonian Open Access reports more than 5.2 million digital items, including 2D and 3D media. The included exporter checks each media record for usage.access = CC0 before adding it.
- Objaverse-XL contains 10M+ 3D objects, but each object has its own license. The exporter selects CC0 and CC BY 4.0 items only.
- Wikimedia Commons has image and video files with different licenses. The exporter reads the license attached to each file and only marks exact allowlisted licenses as verified.
- Open Images lists 9,178,275 images, but the official repository warns that it does not warrant the license status of each individual image. This source is catalogued, not blindly downloaded.
- Meta PE Video contains 998,862 videos and lists CC BY-NC 4.0. It is excluded by default because it is non-commercial.

## Install

Python 3.11+ is recommended. Install the visual training dependencies:

~~~bash
python -m pip install -r multimodal/requirements.txt
~~~

For video frame extraction, install FFmpeg and make ffmpeg and ffprobe available on PATH. For 3D previews, install Blender 3.6+ and run the renderer through Blender's Python runtime. The Objaverse-XL exporter additionally requires the objaverse package:

~~~bash
python -m pip install objaverse
~~~

## 1. Collect CC0 images from Smithsonian Open Access

Register for a free Smithsonian API key and set it only as an environment variable. The exporter never writes the key to the manifest:

~~~bash
export SMITHSONIAN_API_KEY="YOUR_KEY"
python multimodal/export_smithsonian.py --limit 5000 --out datasets/smithsonian_manifest.jsonl
python multimodal/collect.py --manifest datasets/smithsonian_manifest.jsonl --limit 5000 --max-total-gb 8
~~~

The exporter reads the usage flag on each individual media record and only exports items marked CC0. The API key is private: do not paste it into source files, notebooks or GitHub.

## 2. Collect images and videos from Wikimedia Commons

Create a rights-aware manifest. The search result itself is not enough: the script reads each file's own license metadata.

~~~bash
python multimodal/export_wikimedia.py --media image --query "animation drawing character" --limit 2000 --out datasets/wikimedia_images.jsonl
python multimodal/export_wikimedia.py --media video --query "animation motion" --limit 500 --out datasets/wikimedia_videos.jsonl
~~~

Then download only approved records:

~~~bash
python multimodal/collect.py --manifest datasets/wikimedia_images.jsonl --limit 2000 --max-total-gb 8
python multimodal/collect.py --manifest datasets/wikimedia_videos.jsonl --limit 500 --max-total-gb 8
~~~

The collector checks the item-level license, rights_verified, HTTPS URL, file extension and file-size cap. It writes local files under datasets/raw/ and appends their metadata to datasets/assets.jsonl. Files are never uploaded to this Git branch.

## 3. Collect 3D models from Objaverse-XL

The Objaverse-XL API downloads metadata and can enumerate millions of objects. The exporter filters each object by its individual license before downloading any model.

~~~bash
python multimodal/export_objaverse_xl.py --limit 5000 --workers 4
~~~

The initial 5,000 is a safe pilot. Increase --limit only after checking disk space, bandwidth, source terms and the first downloaded sample. The exporter stores models below datasets/raw/objaverse_xl/ and appends item-level metadata to datasets/assets.jsonl.

## 4. Render 3D models into visual training views

CLIP learns from images, so 3D assets must first be rendered into preview images. Blender can create several camera views for each downloaded model:

~~~bash
blender --background --python multimodal/render_3d.py -- --manifest datasets/assets.jsonl --limit 1000 --views 6
~~~

The renderer writes turntable-style views to datasets/previews/. Invalid or unsupported model files are skipped and reported; they are not silently counted as rendered.

## 5. Prepare training pairs

Images are used directly, videos are sampled into a small number of frames using FFmpeg, and 3D models are represented by their Blender-rendered previews. Each frame/view inherits the source asset's caption and rights metadata.

~~~bash
python multimodal/prepare_pairs.py --manifest datasets/assets.jsonl --out datasets/pairs.jsonl --frames-per-video 4
~~~

The generated JSONL contains image paths, descriptions, asset IDs, media types, source URLs and license metadata. It does not copy media into the repository.

## 6. Train the visual learner

The training script uses OpenCLIP ViT-B/32 as a frozen encoder and trains two small projection heads with a contrastive loss. It saves a checkpoint and metrics after every epoch, supports resume, and handles Ctrl+C by saving a checkpoint.

~~~bash
python multimodal/train_visual.py --pairs datasets/pairs.jsonl --epochs 20 --batch-size 16 --output artifacts/multimodal/visual_adapter.pt
~~~

For a longer run, increase --epochs or set --max-steps. The run is finite and reproducible rather than an uncontrolled infinite process. The checkpoint contains the pretrained encoder identifier, learned adapter weights, training counts and license summary.

Run semantic search after training:

~~~bash
python multimodal/search_visual.py --pairs datasets/pairs.jsonl --checkpoint artifacts/multimodal/visual_adapter.pt --query "a dramatic 3D character turntable with rim lighting" --top-k 12
~~~

## Mobile-first training

A modern phone can manage manifests and small pilot downloads, but it is not a suitable place to store millions of images or train a vision encoder for hours. From Android, use Google Colab in the browser, select a GPU runtime when one is available, clone this branch and keep the media/checkpoints in Google Drive. GPU availability and free-tier limits are controlled by Colab and are not guaranteed.

Example Colab setup:

~~~bash
git clone --depth 1 --branch motionforge-multimodal-learning https://github.com/japaguimarassi-create/J.git
cd J
python -m pip install -r multimodal/requirements.txt
~~~

Mount Drive and point --pairs and --output to the corresponding Drive paths. The JSONL image paths must point to files visible from the current Colab runtime.

## Storage and training safety

- Do not place dataset binaries, model weights, API keys or private credentials in Git.
- Keep a copy of assets.jsonl and pairs.jsonl with the media store. A manifest without the matching files cannot train.
- Start with hundreds or a few thousand verified items. Confirm that the downloaded files open and that the captions describe them before scaling up.
- Use --max-total-gb and --max-file-mb on collection. Do not remove these caps just to make a run larger.
- Do not use destructive overwrites for source material. The collector uses stable IDs and hashes to avoid needless duplicate downloads.
- Dataset size is not a quality metric. Remove corrupt, duplicate, mislabeled and rights-unclear files before training.
- A lower contrastive loss only shows that the adapter fits the training pairs; it does not prove general visual understanding or generation quality.

## References

- Smithsonian Open Access: https://www.si.edu/openaccess/faq
- Objaverse / Objaverse-XL: https://objaverse.allenai.org/docs/intro/
- Wikimedia Commons reuse rules: https://commons.wikimedia.org/wiki/Commons:REUSE
- Open Images download and licensing notes: https://storage.googleapis.com/openimages/web/download.html
- Meta PE Video dataset and CC BY-NC 4.0 license: https://ai.meta.com/datasets/pe-video/
