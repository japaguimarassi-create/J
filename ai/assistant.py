import json
import re
import unicodedata
from pathlib import Path

import torch
from torch.nn import functional as F

from model import MAX_SEQ_LEN, encode

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data" / "seed_examples.jsonl"
TEACHER_DATA = ROOT / "data" / "teacher_generated.jsonl"
STOPWORDS = set("a as o os um uma uns umas de da do das dos em no na nos nas para por com sem que como e ou eu voce voces meu minha seu sua ao aos se faz fazer crie criar quero preciso pode poderia sobre qual quais isso isto the and or to of in is how what make create".split())


def normalize(text):
    value = unicodedata.normalize("NFKD", str(text).lower())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return {word for word in re.findall(r"[a-z0-9_]+", value) if len(word) > 1 and word not in STOPWORDS}


def load_examples(path=DEFAULT_DATA):
    rows, seen = [], set()
    paths = [Path(path)]
    if Path(path) == DEFAULT_DATA and TEACHER_DATA.exists():
        paths.append(TEACHER_DATA)
    for data_path in paths:
        if not data_path.exists():
            continue
        with data_path.open("r", encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                item = json.loads(line)
                if item.get("prompt") and item.get("response"):
                    key = (str(item["prompt"]).strip().casefold(), str(item["response"]).strip().casefold())
                    if key not in seen:
                        seen.add(key)
                        rows.append(item)
    return rows


class LocalAssistant:
    def __init__(self, path=DEFAULT_DATA):
        self.examples = load_examples(path)
        self.indexed = [(item, normalize(item["prompt"])) for item in self.examples]

    @staticmethod
    def student_score(model, query, response):
        prefix = "Usuário: " + query + "\nAssistente: "
        full = encode(prefix + response, add_bos=True)
        prefix_length = len(encode(prefix, add_bos=True))
        if len(full) > MAX_SEQ_LEN:
            removed = len(full) - MAX_SEQ_LEN
            full = full[removed:]
            prefix_length = max(1, prefix_length - removed)
        if len(full) < 3 or prefix_length >= len(full):
            return -100.0
        inputs = torch.tensor([full[:-1]], dtype=torch.long)
        targets = torch.tensor(full[1:], dtype=torch.long)
        with torch.no_grad():
            logp = F.log_softmax(model(inputs)[0], dim=-1)
            start = max(0, prefix_length - 1)
            positions = torch.arange(start, len(targets))
            chosen = logp[positions, targets[positions]]
            return float(chosen.mean().item()) if chosen.numel() else -100.0

    def answer(self, query, model=None):
        qtokens = normalize(query)
        ranked = []
        for item, tokens in self.indexed:
            overlap = len(qtokens & tokens)
            precision = overlap / len(qtokens) if qtokens else 0
            recall = overlap / len(tokens) if tokens else 0
            score = 2 * precision * recall / (precision + recall) if precision + recall else 0
            if item["prompt"].strip().casefold() == query.strip().casefold():
                score = 1.0
            ranked.append({"lexical": score, "student": None, "item": item})
        ranked.sort(key=lambda row: row["lexical"], reverse=True)
        candidates = ranked[:6]
        if model is not None:
            model.eval()
            for row in candidates:
                row["student"] = self.student_score(model, query, row["item"]["response"])
            values = [row["student"] for row in candidates]
            lo, hi = min(values), max(values)
            for row in candidates:
                neural = (row["student"] - lo) / (hi - lo) if hi > lo else 0.5
                row["combined"] = 0.9 * row["lexical"] + 0.1 * neural
            candidates.sort(key=lambda row: row["combined"], reverse=True)
        best_row = candidates[0] if candidates else None
        lexical = best_row["lexical"] if best_row else 0
        score = best_row.get("combined", lexical) if best_row else 0
        best = best_row["item"] if best_row else None
        if best and lexical >= 0.22:
            return {
                "answer": best["response"],
                "method": "student_reranked_retrieval" if model is not None else "curated_retrieval",
                "confidence": round(score, 3),
                "student_score": round(best_row["student"], 4) if model is not None else None,
                "matched_prompt": best["prompt"],
                "warning": "Resposta recuperada de exemplos revisáveis; confira se cobre exatamente o pedido.",
            }
        return {
            "answer": "O aluno ainda não tem cobertura confiável para esta solicitação. Reformule como uma tarefa curta de FORGE ou amplie o corpus após revisão dos professores.",
            "method": "low_confidence_fallback",
            "confidence": round(score, 3),
            "student_score": round(best_row["student"], 4) if model is not None and best_row else None,
            "matched_prompt": best["prompt"] if best else None,
            "related_example": best["response"] if best and score > 0 else None,
            "warning": "A geração livre de um modelo com 247.890 parâmetros não é confiável nesta etapa.",
        }
