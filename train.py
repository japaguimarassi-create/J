from __future__ import annotations

import argparse
from pathlib import Path

from datasets import load_dataset
from peft import LoraConfig
from trl import SFTConfig, SFTTrainer


def main() -> None:
    parser = argparse.ArgumentParser(description="Especializa o Enturma com SFT + LoRA.")
    parser.add_argument("--data", nargs="+", default=["data/social_dialogues.jsonl", "data/minecraft_dialogues.jsonl"])
    parser.add_argument("--output", default="output/enturma-lora")
    parser.add_argument("--model", default="Qwen/Qwen3-0.6B")
    parser.add_argument("--epochs", type=float, default=3.0)
    parser.add_argument("--max-length", type=int, default=1024)
    args = parser.parse_args()
    data_paths = [Path(item) for item in args.data]
    missing = [str(path) for path in data_paths if not path.exists()]
    if missing:
        raise SystemExit("Arquivos de dados não encontrados: " + ", ".join(missing))

    dataset = load_dataset("json", data_files=[str(path) for path in data_paths], split="train")
    if "messages" not in dataset.column_names:
        raise SystemExit("Cada linha JSON deve conter a coluna 'messages'.")

    import torch
    has_cuda = torch.cuda.is_available()
    use_bf16 = bool(has_cuda and torch.cuda.is_bf16_supported())
    config = SFTConfig(
        output_dir=args.output,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=2e-4,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        logging_steps=5,
        save_steps=100,
        save_total_limit=3,
        max_length=args.max_length,
        packing=False,
        gradient_checkpointing=True,
        bf16=use_bf16,
        fp16=bool(has_cuda and not use_bf16),
        report_to="none",
        assistant_only_loss=True,
    )
    lora = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules="all-linear",
        task_type="CAUSAL_LM",
    )
    trainer = SFTTrainer(
        model=args.model,
        args=config,
        train_dataset=dataset,
        peft_config=lora,
    )
    trainer.train()
    trainer.save_model(args.output)
    trainer.processing_class.save_pretrained(args.output)
    print(f"Adaptador salvo em: {args.output}")
    print("Compare com o modelo-base em cenários reservados antes de distribuir o adaptador.")


if __name__ == "__main__":
    main()
