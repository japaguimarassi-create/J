# Initial research notes

Research captured for this foundation on 2026-10-21. Recheck upstream pages and revisions before ingesting data; these notes do not grant a blanket license.

## Candidate sources

- [BigCode: The Stack](https://www.bigcode-project.org/docs/about/the-stack/) documents a code dataset selected around license terms, provenance metadata and an opt-out/removal process.
- [The Stack v2 dataset card](https://huggingface.co/datasets/bigcode/the-stack-v2) describes more than 3 billion files across 600+ programming and markup languages. Its current changelog lists v2.2.0 removals for repositories that opted out before 2026-07-29. The card states that bulk file-content access requires an agreement with Software Heritage and INRIA; original source licenses and training principles still apply.
- [The Stack v2 opt-out repository](https://github.com/bigcode-project/opt-out-v2) describes repository-owner removal requests.
- [FineWeb dataset card](https://huggingface.co/datasets/HuggingFaceFW/fineweb) identifies ODC-By 1.0 and describes a web corpus with more than 18.5 trillion tokens. It is far too large to assume that a small prototype can download or train on the whole collection. CommonCrawl terms and dataset governance still need review.
- [FineWeb2 dataset card](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2) describes multilingual web data. Review the current card, language subsets, and exact access/attribution conditions before use.
- [GitHub REST API documentation](https://docs.github.com/en/rest) documents repository search and public API usage. GitHub search has distinct rate limits; Deta should handle limit responses deliberately and avoid request bursts.
- [GitHub REST API best practices](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api) recommends respecting limits, avoiding concurrent polling, and handling retry headers.

## Design consequences

1. Publicly reachable data is not automatically unrestricted for training or redistribution.
2. The registry is a catalogue of candidate sources, not an automatic full-dataset downloader.
3. The initial model has 79,824 trainable parameters. This is a toy byte-prediction baseline, not a substitute for a modern general-purpose model.
4. Deta should use staged subsets, deduplication, held-out evaluations and source-level provenance rather than gathering uncontrolled data.
5. The first code fetcher only searches GitHub repository metadata and retrieves bounded files. It is not yet a universal web crawler or search engine.
6. Initial work is tested Python infrastructure, not Android packaging. No APK is built in this branch.
