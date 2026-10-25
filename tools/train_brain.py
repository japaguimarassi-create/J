import json
import random
import re
import unicodedata
from pathlib import Path

import numpy as np

ROOT = Path("src/main/resources/assets/realityengineai/brain")
ROOT.mkdir(parents=True, exist_ok=True)
VOCABULARY, EMBEDDING, HIDDEN, OUTPUTS = 1000, 256, 120, 24
SEED = 171010
CLASSES = [
    "block_computer", "block_crystal", "block_generic", "entity_dragon",
    "entity_hostile", "entity_creature", "item_sword", "item_tool", "item_food",
    "item_generic", "dimension_desert", "dimension_cold", "dimension_forest",
    "dimension_space", "dimension_infernal", "dimension_generic", "query_mods",
    "query_blocks", "query_items", "query_entities", "query_dimensions",
    "command_enter", "ask_help", "ambiguous"
]
EXAMPLES = {
    "block_computer": ["um computador em bloco", "bloco de computador", "computador como bloco", "pc em bloco", "terminal de computador para colocar", "um bloco computador", "computer block", "máquina de computação em bloco", "cpu como bloco", "terminal com tela e interface", "máquina com painel clicável"],
    "block_crystal": ["um bloco de cristal", "cristal em bloco", "bloco cristalino luminoso", "cristal que emite luz", "bloco de energia azul", "cristal sólido para construir", "glowing crystal block", "bloco de ametista personalizado"],
    "block_generic": ["um bloco de pedra azul", "um bloco personalizado", "um bloco de energia", "bloco que cura ao clicar", "bloco que concede velocidade", "bloco de metal", "uma máquina em bloco", "uma estrutura como bloco", "block", "crie um bloco novo"],
    "entity_dragon": ["um dragão", "um dragão gigante", "uma criatura dragão de cem metros", "dragão com asas", "dragon mob", "um monstro do tipo dragão", "um dragão roxo para spawnar", "uma entidade dragão"],
    "entity_hostile": ["um monstro hostil", "um boss inimigo", "uma criatura agressiva", "um mob que ataca inimigos", "hostile mob", "um zumbi novo", "uma entidade que persegue monstros", "um inimigo para o mundo"],
    "entity_creature": ["uma criatura", "um animal novo", "um mob amigável", "uma entidade viva", "uma criatura que anda", "um animal personalizado", "custom creature", "uma entidade com nome próprio"],
    "item_sword": ["uma espada", "uma espada de energia", "uma katana", "um sabre", "uma lâmina de cristal", "sword item", "uma espada muito forte", "uma arma corpo a corpo tipo espada"],
    "item_tool": ["uma picareta", "um machado", "uma ferramenta de mineração", "uma ferramenta personalizada", "pickaxe item", "uma picareta de cristal", "uma ferramenta para quebrar pedra", "uma ferramenta de diamante"],
    "item_food": ["uma comida", "um pão", "uma fruta", "um alimento que cura fome", "uma carne especial", "food item", "um item comestível", "uma maçã especial"],
    "item_generic": ["um amuleto", "um artefato de cura", "uma varinha de velocidade", "um item", "um objeto encantado", "um artefato", "um item genérico", "um item que concede força ao clicar"],
    "dimension_desert": ["uma dimensão de deserto", "um planeta desértico", "um mundo com dunas", "dimensão de areia", "desert dimension", "um mundo cheio de areia", "uma dimensão seca", "um mundo de dunas escaldantes"],
    "dimension_cold": ["uma dimensão de neve", "um mundo de gelo", "uma dimensão congelada", "planeta frio e nevado", "snow dimension", "mundo coberto de neve", "uma dimensão com geleiras", "um mundo gelado"],
    "dimension_forest": ["uma dimensão de floresta", "mundo com árvores", "uma dimensão de selva", "forest dimension", "planeta florestal", "mundo com florestas densas", "uma dimensão cheia de árvores", "mundo verde"],
    "dimension_space": ["uma dimensão no espaço", "mundo sem céu", "dimensão da galáxia", "um planeta de estrelas", "space dimension", "um universo vazio", "dimensão espacial", "um mundo no vazio cósmico"],
    "dimension_infernal": ["uma dimensão infernal", "mundo de lava e fogo", "um mundo vulcânico", "dimensão de vulcão", "infernal dimension", "uma dimensão quente", "planeta de lava", "mundo das chamas"],
    "dimension_generic": ["uma nova dimensão", "um planeta novo", "um mundo personalizado", "dimensão própria", "new dimension", "um universo diferente", "uma dimensão com terreno próprio", "criar outro mundo"],
    "query_mods": ["lista de mods instalados", "quais mods estão carregados", "mostrar todos os mods", "mod list", "quais mods estão ativos", "nomes dos mods instalados", "catálogo de mods", "quais modificações estão funcionando"],
    "query_blocks": ["liste os blocos registrados", "mostrar catálogo de blocos", "quantos blocos existem", "blocos registrados do forge", "block registry", "listar blocos", "consultar registros de blocos", "quais blocos estão disponíveis"],
    "query_items": ["liste os itens registrados", "mostrar catálogo de itens", "quantos itens existem", "itens registrados do forge", "item registry", "listar itens", "consultar registro de itens", "quais itens estão disponíveis"],
    "query_entities": ["liste as criaturas registradas", "quantas entidades existem", "entity registry", "mostrar mobs registrados", "consultar entidades", "lista de mobs", "quais criaturas estão disponíveis", "catálogo de entidades"],
    "query_dimensions": ["liste as dimensões", "quais dimensões existem", "mostrar mundos registrados", "dimension registry", "consultar dimensões criadas", "lista de dimensões", "quantas dimensões existem", "mostrar dimensões"],
    "command_enter": ["entrar na dimensão 3", "ir para dimensão 4", "teleportar para dimensão 12", "entrar na última dimensão", "enter dimension 5", "visitar o mundo que criei", "ir para a dimensão nova", "entrar nessa dimensão"],
    "ask_help": ["ajuda", "quais comandos existem", "como funciona", "o que você sabe fazer", "mostrar capacidades", "help", "listar comandos disponíveis", "como usar essa IA"],
    "ambiguous": ["faça algo incrível", "crie aquilo", "quero algo poderoso", "surpreenda-me", "make something", "uma coisa muito legal", "crie algo", "não sei o que criar"]
}

def normalize(text):
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in text if not unicodedata.combining(char))

def java_hash(text):
    value = 0
    for char in text:
        value = (31 * value + ord(char)) & 0xffffffff
    return (value & 0x7fffffff) % VOCABULARY

def feature_ids(text):
    words = re.findall(r"[a-z0-9]+", normalize(text))
    values = set(java_hash(word) for word in words)
    values.update(java_hash(words[i] + " " + words[i + 1]) for i in range(len(words) - 1))
    return np.asarray(sorted(values), dtype=np.int32)

def prepare_data():
    rng = random.Random(SEED)
    samples = []
    targets = []
    for index, label in enumerate(CLASSES):
        for phrase in EXAMPLES[label]:
            variants = [
                phrase,
                "crie " + phrase,
                "por favor " + phrase,
                "eu quero " + phrase,
                phrase + " por favor",
                "create " + phrase
            ]
            for sample in variants:
                samples.append(feature_ids(sample))
                targets.append(index)
    order = list(range(len(samples)))
    rng.shuffle(order)
    return [samples[index] for index in order], np.asarray([targets[index] for index in order], dtype=np.int32)

def softmax(logits):
    logits = logits - logits.max(axis=1, keepdims=True)
    values = np.exp(np.clip(logits, -50.0, 0.0))
    return values / values.sum(axis=1, keepdims=True)

def train():
    rng = np.random.default_rng(SEED)
    features, labels = prepare_data()
    embed = rng.normal(0.0, 0.018, (VOCABULARY, EMBEDDING)).astype(np.float32)
    input_bias = np.zeros(EMBEDDING, dtype=np.float32)
    w1 = rng.normal(0.0, 0.055, (EMBEDDING, HIDDEN)).astype(np.float32)
    b1 = np.zeros(HIDDEN, dtype=np.float32)
    w2 = rng.normal(0.0, 0.055, (HIDDEN, OUTPUTS)).astype(np.float32)
    b2 = np.zeros(OUTPUTS, dtype=np.float32)
    parameters = [embed, input_bias, w1, b1, w2, b2]
    first = [np.zeros_like(item) for item in parameters]
    second = [np.zeros_like(item) for item in parameters]
    steps = 0
    learning_rate = 0.007
    batch_size = 48
    epochs = 45

    for epoch in range(epochs):
        order = rng.permutation(len(features))
        epoch_loss = 0.0
        seen = 0
        for start in range(0, len(order), batch_size):
            batch = order[start:start + batch_size]
            ids = [features[int(row)] for row in batch]
            y = labels[batch]
            x = np.empty((len(batch), EMBEDDING), dtype=np.float32)
            for row, feature in enumerate(ids):
                x[row] = embed[feature].mean(axis=0)
            x += input_bias
            z1 = x @ w1 + b1
            a1 = np.maximum(z1, 0.0)
            logits = a1 @ w2 + b2
            probabilities = softmax(logits)
            epoch_loss += float(-np.log(np.maximum(probabilities[np.arange(len(batch)), y], 1e-9)).sum())
            seen += len(batch)

            grad_logits = probabilities.copy()
            grad_logits[np.arange(len(batch)), y] -= 1.0
            grad_logits /= len(batch)
            grad_w2 = a1.T @ grad_logits
            grad_b2 = grad_logits.sum(axis=0)
            grad_a1 = grad_logits @ w2.T
            grad_z1 = grad_a1 * (z1 > 0.0)
            grad_w1 = x.T @ grad_z1
            grad_b1 = grad_z1.sum(axis=0)
            grad_x = grad_z1 @ w1.T
            grad_input_bias = grad_x.sum(axis=0)
            grad_embed = np.zeros_like(embed)
            for row, feature in enumerate(ids):
                np.add.at(grad_embed, feature, grad_x[row] / max(1, len(feature)))

            gradients = [grad_embed, grad_input_bias, grad_w1, grad_b1, grad_w2, grad_b2]
            steps += 1
            for i, (parameter, gradient) in enumerate(zip(parameters, gradients)):
                first[i] = 0.9 * first[i] + 0.1 * gradient
                second[i] = 0.999 * second[i] + 0.001 * gradient * gradient
                corrected_first = first[i] / (1.0 - 0.9 ** steps)
                corrected_second = second[i] / (1.0 - 0.999 ** steps)
                parameter -= learning_rate * corrected_first / (np.sqrt(corrected_second) + 1e-8)
        if (epoch + 1) % 15 == 0:
            print("epoch", epoch + 1, "loss", round(epoch_loss / max(1, seen), 4))

    weights = np.concatenate([item.astype("<f4", copy=False).ravel() for item in parameters])
    assert len(weights) == 300000, "The model must contain exactly 300,000 scalar parameters."
    path = ROOT / "weights.bin"
    with path.open("wb") as handle:
        handle.write(b"REAI300K1")
        weights.tofile(handle)

    correct = 0
    for feature, label in zip(features, labels):
        x = embed[feature].mean(axis=0) + input_bias
        hidden = np.maximum(x @ w1 + b1, 0.0)
        correct += int(np.argmax(hidden @ w2 + b2) == int(label))
    report = {
        "architecture": "1000x256 token/bigram embeddings + 256 input bias + 256x120 dense + 120 hidden bias + 120x24 output + 24 output bias",
        "parameter_count": int(len(weights)),
        "training_examples": len(features),
        "epochs": epochs,
        "training_accuracy": round(correct / max(1, len(features)), 4),
        "labels": CLASSES,
        "weights_file_bytes": path.stat().st_size,
        "note": "Specialized intent classifier; not a general-purpose language, image or video model."
    }
    (ROOT / "training_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    assert path.stat().st_size == 9 + 300000 * 4

if __name__ == "__main__":
    train()
