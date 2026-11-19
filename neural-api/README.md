# Neural API — CreatureChat

A serverless HTTP API designed to accept the OpenAI Chat Completions request/response shape used by CreatureChat.

## Important release status

Version 0.1.0 is a **procedural bootstrap**, not a trained GPT model. It contains:
- An authenticated OpenAI-compatible `POST /v1/chat/completions` endpoint.
- A deterministic lexical tokenizer baseline.
- A procedural intent and response engine.
- A declared target Transformer topology of 12 blocks × 5,120 feed-forward units = 61,440 target units.
- Health, model-list, and tokenization endpoints.

The 61,440 units are an architecture target, not 61,440 learned parameters. No trained Transformer weights are included or loaded in this release. General replies are intentionally identified as bootstrap responses.

## Endpoints

- `GET /` and `GET /health` — public service health.
- `GET /v1/models` — authenticated model listing.
- `POST /v1/tokenize` — authenticated tokenizer inspection.
- `POST /v1/chat/completions` — authenticated OpenAI-compatible chat response.

All protected endpoints require:

```http
Authorization: Bearer YOUR_NEURAL_API_KEY
Content-Type: application/json
```

## Vercel environment variable

Set `NEURAL_API_KEY` in Production, Preview, and Development. Never commit the key to GitHub.

## CreatureChat configuration

```mcfunction
/creaturechat key set YOUR_NEURAL_API_KEY
/creaturechat url set "https://YOUR-VERCEL-DOMAIN/v1/chat/completions"
/creaturechat model set neural-core-0.1
/creaturechat timeout set 30
```

## Local checks

```bash
npm test
```

## Architecture limitation

Vercel Functions are suitable for the API gateway and lightweight procedural logic. They are not the training environment for a large GPT model with persistent weights. The trained model should eventually run on a dedicated inference host; this Vercel API can then become its authenticated gateway.

## Security

- API key comparison uses constant-time comparison.
- Request bodies are limited to 1 MB.
- Responses are not cached.
- No conversation content is persisted by this bootstrap.
- The engine uses only the conversation history included in each request.
