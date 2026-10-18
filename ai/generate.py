import argparse
from pathlib import Path

import sentencepiece as spm
import torch

from ai.config import ModelConfig
from ai.model import KoworkLM


def main():
    parser = argparse.ArgumentParser(description="Generate text from local Kowork weights.")
    parser.add_argument("--checkpoint", default="checkpoints/kowork-10b.pt")
    parser.add_argument("--tokenizer", default="data/processed/kowork.model")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--top-k", type=int, default=40)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    args = parser.parse_args()

    checkpoint_path = Path(args.checkpoint)
    tokenizer_path = Path(args.tokenizer)
    if not checkpoint_path.is_file() or not tokenizer_path.is_file():
        raise SystemExit("A trained checkpoint and matching tokenizer are required.")
    if args.device == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA was requested but is unavailable.")
    device = torch.device("cuda" if args.device == "cuda" or (args.device == "auto" and torch.cuda.is_available()) else "cpu")
    try:
        saved = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        config = ModelConfig(**saved["config"])
        config.validate()
        model = KoworkLM(config, device="meta")
        model.load_state_dict(saved["model"], assign=True)
        del saved
        tokenizer = spm.SentencePieceProcessor(model_file=str(tokenizer_path))
        if tokenizer.get_piece_size() != config.vocab_size:
            raise ValueError("Tokenizer and model vocabulary do not match")
    except Exception as error:
        raise SystemExit("Could not load model files: {}".format(error)) from error

    model.to(device).eval()
    ids = tokenizer.encode(args.prompt, out_type=int)
    if not ids:
        raise SystemExit("Prompt must contain at least one token")
    prompt = torch.tensor([ids], dtype=torch.long, device=device)
    output = model.generate(
        prompt,
        max_new_tokens=args.max_new_tokens,
        eos_token_id=tokenizer.eos_id(),
        temperature=args.temperature,
        top_k=args.top_k,
    )
    print(tokenizer.decode(output[0].tolist()))


if __name__ == "__main__":
    main()
