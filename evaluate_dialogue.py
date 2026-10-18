from __future__ import annotations

import json
from pathlib import Path

SCENARIOS = [
    {
        "name": "Entrar em conversa",
        "context": "Um grupo de colegas conversa no intervalo sobre Minecraft. A pessoa conhece o jogo, mas ainda não participa do grupo.",
        "goal": "Começar a participar sem forçar intimidade.",
        "mode": "enturmar",
        "message": "Eles estão falando de uma atualização que eu ainda não joguei. O que eu digo?",
        "checks": ["contexto", "natural", "pergunta"],
    },
    {
        "name": "Resposta curta e casual",
        "context": "Conversa por mensagem entre conhecidos.",
        "goal": "Manter o papo aberto, sem parecer insistente.",
        "mode": "conversar",
        "message": "Kkkkk hoje foi um caos na escola",
        "checks": ["reciprocidade", "sem exagero"],
    },
    {
        "name": "Discordar com respeito",
        "context": "Uma roda de amigos discute qual jogo é melhor.",
        "goal": "Dar uma opinião diferente sem causar briga.",
        "mode": "enturmar",
        "message": "Todo mundo prefere o jogo A, mas eu gosto mais do B.",
        "checks": ["respeito", "especificidade"],
    },
    {
        "name": "Lidar com pouco interesse",
        "context": "A pessoa enviou uma mensagem e recebeu apenas 'ata'.",
        "goal": "Não insistir de forma desconfortável.",
        "mode": "enturmar",
        "message": "Como continuo?",
        "checks": ["limites", "sem pressão"],
    },
]


def main() -> None:
    output = Path("evaluation_scenarios.json")
    output.write_text(json.dumps(SCENARIOS, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Cenários de avaliação gravados em {output.resolve()}")
    print("Execute os cenários no app e avalie de 1 a 5: naturalidade, aderência ao contexto, continuidade, adequação do tom, clareza e respeito a limites.")


if __name__ == "__main__":
    main()
