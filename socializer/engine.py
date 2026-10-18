from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

from .core import build_system_prompt
from .game import build_game_prompt, normalize_game_reply


class LocalModel:
    def __init__(self) -> None:
        self.model = None
        self.tokenizer = None
        self.lock = threading.RLock()
        self.model_id = os.getenv("ENTURMA_MODEL", "Qwen/Qwen3-0.6B")
        self.adapter_path = os.getenv("ENTURMA_ADAPTER", "").strip()
        self.last_error: str | None = None

    def status(self) -> dict[str, Any]:
        return {
            "loaded": self.model is not None,
            "model": self.model_id,
            "adapter": self.adapter_path or None,
            "runtime": "local inference",
            "last_error": self.last_error,
            "note": "Os pesos serão baixados na primeira conversa se ainda não estiverem em cache."
        }

    def load(self) -> None:
        if self.model is not None:
            return
        with self.lock:
            if self.model is not None:
                return
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, trust_remote_code=False)
            if torch.cuda.is_available():
                dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_id, torch_dtype=dtype, device_map="auto", trust_remote_code=False,
                )
            else:
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_id, torch_dtype=torch.float32, trust_remote_code=False,
                )
                self.model.to("cpu")
            if self.adapter_path:
                if not Path(self.adapter_path).exists():
                    raise FileNotFoundError(f"Adaptador ENTURMA_ADAPTER não encontrado: {self.adapter_path}")
                from peft import PeftModel
                self.model = PeftModel.from_pretrained(self.model, self.adapter_path, is_trainable=False)
            self.model.eval()
            self.last_error = None

    def generate(self, messages: list[dict[str, str]], max_new_tokens: int | None = None, temperature: float = 0.72) -> str:
        self.load()
        import torch
        with self.lock, torch.inference_mode():
            try:
                input_ids = self.tokenizer.apply_chat_template(
                    messages, tokenize=True, add_generation_prompt=True,
                    enable_thinking=False, return_tensors="pt",
                )
            except TypeError:
                input_ids = self.tokenizer.apply_chat_template(
                    messages, tokenize=True, add_generation_prompt=True, return_tensors="pt",
                )
            input_ids = input_ids.to(self.model.get_input_embeddings().weight.device)
            if max_new_tokens is None:
                max_new_tokens = max(32, min(512, int(os.getenv("ENTURMA_MAX_NEW_TOKENS", "180"))))
            options: dict[str, Any] = {
                "max_new_tokens": max(32, min(800, int(max_new_tokens))),
                "do_sample": True,
                "temperature": max(0.2, min(1.2, temperature)),
                "top_p": 0.88,
                "repetition_penalty": 1.12,
                "pad_token_id": self.tokenizer.eos_token_id,
            }
            if isinstance(self.tokenizer.eos_token_id, int):
                options["eos_token_id"] = self.tokenizer.eos_token_id
            output = self.model.generate(input_ids=input_ids, **options)
            generated = output[0][input_ids.shape[-1]:]
            text = self.tokenizer.decode(generated, skip_special_tokens=True).strip()
            if "</think>" in text:
                text = text.split("</think>", 1)[1].strip()
            return text

    def reply(self, history: list[dict[str, str]], context: str, goal: str, mode: str, tone: str) -> str:
        max_history = max(2, int(os.getenv("ENTURMA_MAX_HISTORY", "16")))
        messages = [{"role": "system", "content": build_system_prompt(context, goal, mode, tone)}]
        messages.extend(history[-max_history:])
        result = self.generate(messages)
        return result or "Me dá mais um detalhe? Quero entender a situação para continuar o papo de um jeito natural."

    def reply_mob(self, payload: dict[str, Any], knowledge: str = "") -> dict[str, Any]:
        system = build_game_prompt(payload, knowledge)
        history = list(payload.get("history") or [])
        current_message = str(payload.get("player_message", "Oi"))[:2000]
        if history and isinstance(history[-1], dict) and history[-1].get("role") == "user" and history[-1].get("content") == current_message:
            history = history[:-1]
        messages = [{"role": "system", "content": system}]
        for entry in history[-8:]:
            if isinstance(entry, dict) and entry.get("role") in {"user", "assistant"} and isinstance(entry.get("content"), str):
                messages.append({"role": entry["role"], "content": entry["content"][:1000]})
        messages.append({"role": "user", "content": current_message})
        raw = self.generate(messages, max_new_tokens=250, temperature=0.8)
        return normalize_game_reply(raw, payload)
