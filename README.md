# Deta AI 0.3.1

Deta is an experimental developer assistant without a hosted generative-AI API. The Python core combines public-web research, a persistent local knowledge index, offline starter-project generation, a 400,000-parameter grouped neural model, licensed-source ingestion, and code verification.

The mobile integration now includes a native Android HUD, public-web retrieval without an AI-model API, local project creation and a pure-Java runtime for the trained neural model. The APK pipeline runs only after Python tests and Android compilation pass, then tests model loading and generation on an emulator.

## What works now

- **Internet research:** search public pages and extract text from HTTPS websites without an OpenAI/Gemini API key.
- **Source-grounded answers:** the ask command retrieves web pages, indexes their text locally, ranks relevant passages and returns source links. This is retrieval, not a full generative LLM.
- **Local knowledge index:** saved at ~/.local/share/deta/knowledge.json by default. Set DETA_HOME to change Deta's local data directory.
- **Project creation:** generate a playable browser mini-game, a social-feed prototype with local posts/search/likes/comments, or a Python task-management CLI.
- **Four-pass verification:** supported-format parsing, configured static checks, explicit tests, and source/license/similarity checks.
- **Sequential neural training:** five groups of 80,000 trainable parameters each, checkpointing, fixed validation samples, warm-start fine-tuning and lineage metadata.
- **Licensed-source collection:** curated GitHub code sources, per-record provenance, SPDX checks where present, secret-pattern filtering and deduplication.

## No AI API — an important distinction

Deta does not call a hosted generative-AI service. Search uses DuckDuckGo's public HTML results and page requests go directly to public HTTPS websites. Search terms are sent to the search engine to retrieve results. Some websites may block automated requests or return no extractable text.

The ask command in the Python core uses retrieval and passage ranking. In Android, factual searches are handled separately from neural generation: the bundled 400k byte-level model can generate local code continuations, but it is not a general-purpose conversational LLM and can produce malformed or incoherent output. More training helps this small model learn its corpus, but 400,000 parameters cannot make it equivalent to a modern pretrained general-purpose LLM.

## Install and test

Python 3.11+, PyTorch 2.2+, pytest and Ruff are used.

~~~bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m deta.cli doctor
python -m deta.cli count-params
python -m pytest -q
python -m ruff check --select E4,E7,E9,F401,F63,F7,F82 deta tests scripts
~~~

PyTorch training may not work on every Termux/Android installation. A supported Linux runner is currently used for model training.

## Research the internet

~~~bash
python -m deta.cli ask "How do Python iterators work?"
python -m deta.cli ask "Como funciona uma rede neural recorrente?"
python -m deta.cli web-search "Android app architecture" --limit 5
python -m deta.cli read-url https://docs.python.org/3/library/asyncio.html
~~~

The ask command reads up to three search-result pages by default and stores extracted text in the local index. Tune with --results and --read-pages. Search the local index without using the internet:

~~~bash
python -m deta.cli ask "iterators and lazy evaluation" --offline
python -m deta.cli knowledge
python -m deta.cli knowledge --query "GRU training" --limit 5
~~~

Delete the local index with python -m deta.cli clear-knowledge --yes. The index preserves source URLs and content hashes; it is separate from the neural training corpus.

Only public HTTPS hosts are accepted. Local/private IP addresses, local hostnames, embedded URL credentials and non-HTTPS URLs are rejected. Deta does not sign in or bypass website access controls.

## Generate starter projects

### Browser game

~~~bash
python -m deta.cli create-project --kind browser-game --name "Neon Target" --output projects/neon-target --brief "A mobile-friendly reflex game"
~~~

Open projects/neon-target/index.html in a browser. The generated game has a 30-second round, touch/mouse controls, score, timer, local best score and restart.

### Social-feed prototype

~~~bash
python -m deta.cli create-project --kind social-app --name "Community Space" --output projects/community --brief "A simple feed for sharing game ideas"
~~~

The feed supports local post creation, search, likes, comments, deletion and browser storage. It is an offline prototype, not a multi-user social network: accounts, a backend, moderation and server synchronization are not implemented.

### Python CLI tool

~~~bash
python -m deta.cli create-project --kind python-cli --name "Task Organizer" --output projects/task-organizer
~~~

The generated command-line program has add/list/done/remove task commands and stores task data locally. Supported kinds are browser-game, social-app and python-cli. Existing non-empty output directories are rejected to prevent accidental overwrites.

## Use the trained model locally

After downloading a Deta checkpoint, you can run experimental byte-level completion with no hosted model API:

~~~bash
python -m deta.cli model-complete --checkpoint checkpoints/deta-400k/final.pt --prompt "def add(a, b):" --tokens 120 --temperature 0.8 --top-k 24
~~~

This invokes the trained neural weights and produces a continuation from the supplied prompt. It is a small byte-prediction model, so generated output may be malformed or incoherent. Use it as an experimental code-completion tool, not as a source of factual answers or a replacement for code review. For researched factual answers, use the ask command and inspect its cited sources.

## Neural model and extended training

The model has **400,000 actual trainable parameters**, divided into five groups of 80,000. The original 79,824-parameter baseline remains available. Each group is trained in sequence and receives its own checkpoint; a completed run writes final.pt.

The training pipeline now considers 20 public GitHub repositories with up to 20 source files each. A full pass uses **5,000 optimizer updates per group**, or **25,000 new updates across five groups**. The workflow downloads the previously trained model and warm-starts the expanded training pass, preserving learned weights and recording parent checkpoint/dataset hashes. All groups are compared against the same held-out validation batch.

GitHub Actions runs the test suite before training. Only a commit explicitly tagged with [train-deta] starts the long training job. The resulting checkpoints, licensed manifest and source report are uploaded as an artifact.

~~~bash
python -m deta.cli train --data data/approved.jsonl --output-dir checkpoints/deta-400k --initial-weights checkpoints/previous/final.pt --steps-per-group 5000 --start-group 1 --end-group 5 --seed 42
~~~

For a partial staged run, resume groups 4–5 from group 3 using the same manifest and configuration:

~~~bash
python -m deta.cli train --data data/approved.jsonl --output-dir checkpoints/deta-400k --steps-per-group 5000 --start-group 4 --end-group 5 --resume-from checkpoints/deta-400k/group-03.pt --seed 42
~~~

A resume is rejected if the manifest hash, architecture, seed, corpus budget or preceding group does not match. The warm-start option begins a new pass using the prior model and may use a new approved dataset; the checkpoint records the lineage.

## Data governance

Public access is not blanket permission to train. Pages saved in the local knowledge index are not automatically added to the neural training corpus. Review source licenses, attribution, opt-out/removal processes, dataset agreements and privacy terms before adding training data.

The Stack v2, FineWeb and FineWeb2 are source candidates, not entire corpora downloaded silently. The Stack v2 dataset card states that bulk source-content access requires an agreement with Software Heritage and INRIA; Deta does not bypass that requirement. See docs/DATA_GOVERNANCE.md and docs/RESEARCH.md.

## Android app integration

The Android implementation now includes:
- A native dark Deta HUD with on-device conversation history, local source memory and clickable web citations.
- Direct HTTPS search/read of public pages, bounded downloads and validation of redirects.
- Local starter-project generation for browser games, social-feed prototypes and web apps. The Library opens a WebView preview and can share generated HTML.
- A custom Deta launcher mark and original promotional artwork.
- The trained 400,000-parameter checkpoint exported to a compact binary asset. A pure-Java GRU runtime verifies its SHA-256, loads the weights and can perform experimental code continuation with the #neural prefix. No hosted AI API key is required.

The app creates starter HTML projects; it does not yet package every user-created project as its own standalone APK. These templates are local prototypes, not multi-user production services.

## Android validation and APK

The CI pipeline gates APK packaging on Python unit tests, static checks, generated-project smoke tests and Android Java/resource compilation. It then exports the trained checkpoint, assembles the debug APK, runs Android-emulator instrumentation tests against the embedded model, and verifies alignment, signature, ZIP integrity and package identity before artifact upload.

The package is app.deta.mobile.debug. The APK is debug-signed for direct installation and testing, not for Play Store publication.
