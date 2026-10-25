import argparse
import json
import os
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEACHERS = {
    "qwen": os.getenv("MOTIONFORGE_TEACHER_QWEN", "qwen3:8b"),
    "gemma": os.getenv("MOTIONFORGE_TEACHER_GEMMA", "gemma4:e4b"),
    "gpt_oss": os.getenv("MOTIONFORGE_TEACHER_GPT_OSS", "gpt-oss:20b"),
}
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
KEEP_ALIVE = os.getenv("MOTIONFORGE_KEEP_ALIVE", "0s")


def ask(model, prompt, timeout=900):
    payload = json.dumps({
        "model": model, "stream": False, "keep_alive": KEEP_ALIVE,
        "messages": [
            {"role": "system", "content": "Você é professor técnico do MotionForge e da linguagem FORGE. Responda em português; não invente recursos, use exemplos curtos e indique limites."},
            {"role": "user", "content": prompt},
        ],
        "options": {"temperature": 0.2, "num_ctx": 4096, "num_predict": 900},
    }).encode("utf-8")
    request = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["message"]["content"].strip()
    except Exception as exc:
        raise RuntimeError("Falha no professor local " + model + ": " + str(exc)) from exc


def extract_json(text):
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        raise ValueError("O modelo não retornou um objeto JSON válido.")
    return json.loads(match.group(0))


def valid_score(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 1 <= value <= 5


def tally_approvals(reviews):
    result = {}
    for name in TEACHERS:
        review = reviews.get(name, {})
        result[name] = review.get("approve") is True and valid_score(review.get("score")) and review["score"] >= 4
    return result, all(result.values())


def run_brainstorm(topic, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    proposals = {}
    for name, model in TEACHERS.items():
        answer = ask(model, "Proponha uma solução concreta para a tarefa. Inclua plano, script FORGE válido e limites, distinguindo o que existe do que é futuro. Tarefa: " + topic)
        proposals[name] = {"model": model, "proposal": answer}
    proposal_text = "\n\n".join("PROPOSTA " + key + " (" + item["model"] + "):\n" + item["proposal"] for key, item in proposals.items())
    score_template = {"scores": {key: {"technical": 5, "useful": 5, "learnable": 5, "testable": 5} for key in TEACHERS}, "risks": ["riscos concretos"]}
    critiques = {}
    for name, model in TEACHERS.items():
        prompt = "Avalie cada proposta de modo independente. Dê notas inteiras 1-5 para correção técnica, utilidade, possibilidade de aprender em modelo pequeno e facilidade de teste. Responda somente JSON com esta forma: " + json.dumps(score_template) + "\n\n" + proposal_text
        critiques[name] = extract_json(ask(model, prompt))
    scores = {key: [] for key in TEACHERS}
    for review in critiques.values():
        for candidate in TEACHERS:
            fields = review.get("scores", {}).get(candidate, {})
            values = [fields.get(k) for k in ("technical", "useful", "learnable", "testable")]
            if all(valid_score(v) for v in values):
                scores[candidate].append(sum(values) / len(values))
    averages = {key: (sum(vals) / len(vals) if vals else 0) for key, vals in scores.items()}
    winner = max(averages, key=averages.get)
    synthesis = ask(TEACHERS[winner], "Crie uma síntese final técnica, curta, testável e adequada ao aluno de 250 mil parâmetros. Combine somente pontos sustentados, inclua um exemplo FORGE e declare incertezas. Não invente funções. Tarefa: " + topic + "\n\nPropostas e críticas:\n" + proposal_text + "\n" + json.dumps(critiques, ensure_ascii=False))
    final_reviews = {}
    approval_template = {"approve": True, "score": 5, "risks": []}
    for name, model in TEACHERS.items():
        prompt = "Revisor final independente: aprove somente se a síntese for tecnicamente plausível, útil e compatível com a gramática documentada. Retorne apenas JSON neste formato: " + json.dumps(approval_template) + "\nPedido: " + topic + "\nSíntese:\n" + synthesis
        final_reviews[name] = extract_json(ask(model, prompt))
    approvals, unanimous = tally_approvals(final_reviews)
    record = {
        "topic": topic, "winner": winner, "averages": averages, "proposals": proposals,
        "critiques": critiques, "synthesis": synthesis, "final_reviews": final_reviews,
        "approvals": approvals, "approved_for_training": unanimous,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with (out_dir / "teacher_brainstorm.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    if unanimous:
        row = {"prompt": topic, "response": synthesis, "source": "three_teacher_consensus", "winner": winner, "scores": averages, "approvals": approvals}
        with (out_dir / "teacher_generated.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("topic", nargs="+")
    parser.add_argument("--out", type=Path, default=ROOT / "data")
    args = parser.parse_args()
    result = run_brainstorm(" ".join(args.topic), args.out)
    print(json.dumps({key: result[key] for key in ("winner", "averages", "approved_for_training", "approvals", "synthesis")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
