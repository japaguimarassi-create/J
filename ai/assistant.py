from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import torch
from torch.nn import functional as F

from ai.student import BLOCK_SIZE, BOS_ID, EOS_ID, ByteBPETokenizer, ForgeStudent, VOCAB_SIZE

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = ROOT / "data" / "seed.jsonl"
OPTIONAL_CORPUS = ROOT / "data" / "distilled.jsonl"
STOPWORDS = set("a as o os um uma uns umas de da do das dos em no na nos nas para por com sem que como e ou eu voce voces meu minha seu sua ao aos se faz fazer crie criar quero preciso pode poderia sobre qual quais isso isto the and or to of in is how what make create".split())
SYNONYMS = {
    "bola": "circulo", "esfera": "circulo", "girar": "rotacao",
    "girando": "rotacao", "rotacionar": "rotacao", "animacao": "animar",
    "animar": "animacao", "quadro": "keyframe", "quadros": "keyframe",
    "quadros-chave": "keyframe", "desenho": "2d", "tridimensional": "3d",
}


def normalize_words(text: str) -> set[str]:
    value = unicodedata.normalize("NFKD", str(text).lower())
    value = "".join(char for char in value if not unicodedata.combining(char))
    words = {word for word in re.findall(r"[a-z0-9_]+", value) if len(word) > 1 and word not in STOPWORDS}
    expanded = set(words)
    for word in words:
        if word in SYNONYMS:
            expanded.add(SYNONYMS[word])
    return expanded


def load_corpus(paths: list[Path] | None = None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for path in paths or [DEFAULT_CORPUS, OPTIONAL_CORPUS]:
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(str(path) + ":" + str(line_number) + ": JSON inválido") from exc
                prompt = item.get("prompt")
                response = item.get("response")
                if not isinstance(prompt, str) or not isinstance(response, str) or not prompt.strip() or not response.strip():
                    continue
                key = (prompt.strip().casefold(), response.strip().casefold())
                if key not in seen:
                    seen.add(key)
                    rows.append({"prompt": prompt.strip(), "response": response.strip(), "source": str(item.get("source", "curated"))})
    return rows


def lexical_score(query: str, candidate: str) -> float:
    query_words, candidate_words = normalize_words(query), normalize_words(candidate)
    if query.strip().casefold() == candidate.strip().casefold():
        return 1.0
    overlap = len(query_words & candidate_words)
    if not overlap:
        return 0.0
    precision = overlap / max(1, len(query_words))
    recall = overlap / max(1, len(candidate_words))
    return 2 * precision * recall / max(1e-9, precision + recall)


def student_log_score(model: ForgeStudent, tokenizer: ByteBPETokenizer, prompt: str, source: str, response: str) -> float:
    prefix = "Usuário: " + prompt + "\nContexto FORGE:\n" + source[:1500] + "\nForge AI:"
    combined = prefix + "\n" + response
    full_ids = [BOS_ID] + tokenizer.encode(combined) + [EOS_ID]
    prefix_length = 1 + len(tokenizer.encode(prefix))
    if len(full_ids) > BLOCK_SIZE + 1:
        removed = len(full_ids) - (BLOCK_SIZE + 1)
        full_ids = full_ids[removed:]
        prefix_length = max(1, prefix_length - removed)
    if len(full_ids) < 3:
        return -100.0
    inputs = torch.tensor(full_ids[:-1], dtype=torch.long).unsqueeze(0)
    targets = torch.tensor(full_ids[1:], dtype=torch.long)
    with torch.no_grad():
        logits = model(inputs)[0]
        log_probs = F.log_softmax(logits, dim=-1)
        first_target = max(0, prefix_length - 1)
        positions = torch.arange(first_target, targets.numel())
        if positions.numel() == 0:
            return -100.0
        scores = log_probs[positions, targets[positions]]
        return float(scores.mean().item())


class StudentAssistant:
    def __init__(self, corpus_paths: list[Path] | None = None):
        self.corpus_paths = corpus_paths or [DEFAULT_CORPUS, OPTIONAL_CORPUS]

    def answer(self, prompt: str, source: str = "", model: ForgeStudent | None = None,
               tokenizer: ByteBPETokenizer | None = None) -> dict[str, Any]:
        examples = load_corpus(self.corpus_paths)
        ranked = [{"item": item, "lexical": lexical_score(prompt, item["prompt"]), "neural": None}
                  for item in examples]
        ranked.sort(key=lambda row: row["lexical"], reverse=True)
        candidates = ranked[:8]
        if model is not None and tokenizer is not None:
            model.eval()
            for row in candidates:
                row["neural"] = student_log_score(model, tokenizer, prompt, source, row["item"]["response"])
            values = [float(row["neural"]) for row in candidates]
            minimum, maximum = min(values), max(values)
            for row in candidates:
                neural = ((float(row["neural"]) - minimum) / (maximum - minimum)) if maximum > minimum else 0.5
                row["combined"] = 0.88 * row["lexical"] + 0.12 * neural
        else:
            for row in candidates:
                row["combined"] = row["lexical"]
        if not candidates or candidates[0]["lexical"] < 0.16:
            related = candidates[0] if candidates and candidates[0]["lexical"] >= 0.04 else None
            response = "Ainda não tenho cobertura confiável para responder a esse pedido com o aluno de 250 mil parâmetros. Reformule como uma tarefa curta de FORGE, acrescente um exemplo aprovado pelos três professores ou use o modo Brainstorm."
            if related:
                response += "\n\nExemplo relacionado: " + related["item"]["response"]
            return {
                "response": response, "mode": "student", "confidence": round(candidates[0]["lexical"], 3) if candidates else 0.0,
                "lexical_score": round(candidates[0]["lexical"], 3) if candidates else 0.0,
                "student_score": round(float(candidates[0]["neural"]), 4) if model is not None and candidates else None,
                "matched_prompt": related["item"]["prompt"] if related else None,
                "warning": "O aluno usa recuperação de exemplos e reordenação neural; não gera texto livre não verificado."
            }
        candidates.sort(key=lambda row: row["combined"], reverse=True)
        best = candidates[0]
        return {
            "response": best["item"]["response"], "mode": "student" if model is not None else "retrieval",
            "confidence": round(best["combined"], 3), "lexical_score": round(best["lexical"], 3),
            "student_score": round(float(best["neural"]), 4) if model is not None else None,
            "matched_prompt": best["item"]["prompt"], "source": best["item"].get("source", "curated"),
            "warning": "Resposta recuperada de exemplos revisados; confira se atende exatamente ao pedido."
        }
