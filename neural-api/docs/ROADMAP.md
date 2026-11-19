# Neural Core Roadmap

## Stage 0.1 — API bootstrap
- [x] Vercel serverless API structure
- [x] OpenAI-compatible chat response format
- [x] API key authentication
- [x] Deterministic tokenizer baseline
- [x] Procedural intent engine
- [x] Declare minimum target topology of 60,000 units
- [ ] Trained model weights

## Stage 0.2 — Neural implementation
- [ ] Implement a real decoder-only Transformer
- [ ] Implement learned token embeddings and output projection
- [ ] Replace lexical hash IDs with trained tokenizer vocabulary and merges
- [ ] Add deterministic model serialization and checksums
- [ ] Add unit and integration tests for numerical correctness

## Stage 0.3 — Training
- [ ] Prepare legally usable Portuguese and Minecraft dialogue datasets
- [ ] Implement next-token pretraining
- [ ] Implement instruction fine-tuning
- [ ] Evaluate perplexity and dialogue quality
- [ ] Export a versioned inference artifact

## Stage 0.4 — Hosted inference
- [ ] Host trained weights on an inference service sized for the model
- [ ] Keep Vercel as authenticated API gateway if needed
- [ ] Add bounded timeouts, concurrency control, and observability
- [ ] Add persistent memory only after choosing a durable database

No stage is marked complete until its tests and artifacts exist.