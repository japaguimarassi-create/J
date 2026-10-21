# Initial research notes

Research captured for this foundation on 2026-10-21. Recheck upstream pages and revisions before ingesting data; this document is not a blanket license.

## Candidate sources

- [BigCode: The Stack](https://www.bigcode-project.org/docs/about/the-stack/) documents a code dataset built around selected licenses, provenance metadata and an opt-out/removal process.
- [The Stack v2 dataset card](https://huggingface.co/datasets/bigcode/the-stack-v2) reports more than 3 billion files across 600+ programming and markup languages. It also states that bulk content access requires an agreement with Software Heritage and INRIA, and that the original file licenses apply.
- [The Stack v2 opt-out repository](https://github.com/bigcode-project/opt-out-v2) describes repository-owner removal requests.
- [FineWeb dataset card](https://huggingface.co/datasets/HuggingFaceFW/fineweb) identifies ODC-By 1.0 and describes a very large English web corpus. Its scale makes full training unrealistic for this prototype; select reviewed subsets.
- [FineWeb2 dataset card](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2) describes multilingual web data under ODC-By 1.0. Review language subsets and the latest card before use.
- [GitHub REST API documentation](https://docs.github.com/en/rest) is the reference for repository discovery and API limits.

## Design consequences

1. Publicly available is not synonymous with unrestricted use. Deta requires explicit allowlisted license metadata and per-record provenance.
2. The source registry is a catalogue, not an automatic bulk downloader.
3. The v0.1.0 model has 79,824 trainable parameters. This is a toy training baseline, not a replacement for a modern general-purpose model.
4. The initial work is data processing and tested Python infrastructure, not Android packaging. No APK is built in this branch.
