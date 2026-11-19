import argparse
import hashlib
import json
import math
import os
import random
import sqlite3
import time
from collections import Counter
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F


HIDDEN_SIZE = 1024
NUM_LAYERS = 14
NUM_HEADS = 16
VOCAB_SIZE = 8192
MAX_SEQUENCE = 256
NUM_ACTIONS = 256
SPECIAL_BOS = 256
SPECIAL_EOS = 257
SPECIAL_PAD = 258
BASE_VOCAB_SIZE = 259


class BPETokenizer:
    def __init__(self, vocab_size=VOCAB_SIZE):
        self.vocab_size = vocab_size
        self.vocab = [bytes([i]) for i in range(256)]
        self.vocab.extend([b"<BOS>", b"<EOS>", b"<PAD>"])
        self.token_to_id = {token: index for index, token in enumerate(self.vocab[:256])}
        self.merges = []

    @property
    def active_vocab_size(self):
        return len(self.vocab)

    def train(self, texts):
        sequences = [list(text.encode("utf-8")) for text in texts if text]
        sequences = [[bytes([value]) for value in sequence] for sequence in sequences]
        while len(self.vocab) < self.vocab_size:
            counts = Counter()
            for sequence in sequences:
                counts.update(zip(sequence, sequence[1:]))
            selected = None
            for pair, frequency in counts.most_common():
                if frequency < 2:
                    break
                merged = pair[0] + pair[1]
                if merged not in self.token_to_id:
                    selected = (pair, merged)
                    break
            if selected is None:
                break
            pair, merged = selected
            self.merges.append(pair)
            self.token_to_id[merged] = len(self.vocab)
            self.vocab.append(merged)
            updated = []
            for sequence in sequences:
                output = []
                index = 0
                while index < len(sequence):
                    if index + 1 < len(sequence) and sequence[index] == pair[0] and sequence[index + 1] == pair[1]:
                        output.append(merged)
                        index += 2
                    else:
                        output.append(sequence[index])
                        index += 1
                updated.append(output)
            sequences = updated
        return self

    def encode(self, text, special_tokens=True):
        sequence = [bytes([value]) for value in text.encode("utf-8")]
        for left, right in self.merges:
            merged = left + right
            output = []
            index = 0
            while index < len(sequence):
                if index + 1 < len(sequence) and sequence[index] == left and sequence[index + 1] == right:
                    output.append(merged)
                    index += 2
                else:
                    output.append(sequence[index])
                    index += 1
            sequence = output
        ids = [self.token_to_id[piece] for piece in sequence]
        return ([SPECIAL_BOS] + ids + [SPECIAL_EOS]) if special_tokens else ids

    def decode(self, token_ids):
        pieces = []
        for token_id in token_ids:
            if 0 <= int(token_id) < len(self.vocab) and (int(token_id) < 256 or int(token_id) >= BASE_VOCAB_SIZE):
                pieces.append(self.vocab[int(token_id)])
        return b"".join(pieces).decode("utf-8", errors="replace")

    def load_merges(self, rows):
        self.vocab = [bytes([i]) for i in range(256)]
        self.vocab.extend([b"<BOS>", b"<EOS>", b"<PAD>"])
        self.token_to_id = {token: index for index, token in enumerate(self.vocab[:256])}
        self.merges = []
        for left, right, merged in rows:
            left = bytes(left)
            right = bytes(right)
            merged = bytes(merged)
            self.merges.append((left, right))
            self.token_to_id[merged] = len(self.vocab)
            self.vocab.append(merged)


class SQLMemory:
    def __init__(self, path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.create_schema()

    def create_schema(self):
        self.connection.executescript(
            """
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=NORMAL;
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS training_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT NOT NULL,
                input_text TEXT NOT NULL DEFAULT '',
                target_text TEXT NOT NULL DEFAULT '',
                observation_json TEXT NOT NULL DEFAULT '{}',
                action TEXT NOT NULL DEFAULT '',
                reward REAL NOT NULL DEFAULT 0,
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tokenizer_merges (
                rank INTEGER PRIMARY KEY,
                left_token BLOB NOT NULL,
                right_token BLOB NOT NULL,
                merged_token BLOB NOT NULL
            );
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def log_event(self, kind, payload):
        self.connection.execute(
            "INSERT INTO observations(kind,payload,created_at) VALUES(?,?,?)",
            (kind, json.dumps(payload, ensure_ascii=False), time.time())
        )
        self.connection.commit()

    def record_chat(self, prompt, response):
        payload = {"prompt": prompt, "response": response}
        now = time.time()
        self.connection.execute(
            "INSERT INTO observations(kind,payload,created_at) VALUES(?,?,?)",
            ("chat", json.dumps(payload, ensure_ascii=False), now)
        )
        self.connection.execute(
            "INSERT INTO training_samples(task,input_text,target_text,created_at) VALUES(?,?,?,?)",
            ("chat", prompt, response, now)
        )
        self.connection.commit()

    def record_game(self, observation, action="", reward=0.0):
        payload = {"observation": observation, "action": action, "reward": float(reward)}
        now = time.time()
        self.connection.execute(
            "INSERT INTO observations(kind,payload,created_at) VALUES(?,?,?)",
            ("game", json.dumps(payload, ensure_ascii=False), now)
        )
        if action:
            self.connection.execute(
                "INSERT INTO training_samples(task,observation_json,action,reward,created_at) VALUES(?,?,?,?,?)",
                ("game", json.dumps(observation, ensure_ascii=False), str(action), float(reward), now)
            )
        self.connection.commit()

    def recent_events(self, limit=8):
        rows = self.connection.execute(
            "SELECT kind,payload FROM observations ORDER BY id DESC LIMIT ?",
            (int(limit),)
        ).fetchall()
        return list(reversed(rows))

    def corpus(self, limit=50000):
        rows = self.connection.execute(
            "SELECT input_text,target_text,observation_json,action FROM training_samples ORDER BY id DESC LIMIT ?",
            (int(limit),)
        ).fetchall()
        texts = []
        for row in rows:
            texts.extend([row["input_text"], row["target_text"], row["observation_json"], row["action"]])
        return [text for text in texts if text]

    def save_tokenizer(self, tokenizer):
        with self.connection:
            self.connection.execute("DELETE FROM tokenizer_merges")
            self.connection.executemany(
                "INSERT INTO tokenizer_merges(rank,left_token,right_token,merged_token) VALUES(?,?,?,?)",
                [
                    (rank, left, right, left + right)
                    for rank, (left, right) in enumerate(tokenizer.merges)
                ]
            )
            self.connection.execute(
                "INSERT OR REPLACE INTO metadata(key,value) VALUES('tokenizer_vocab_size',?)",
                (str(tokenizer.vocab_size),)
            )

    def load_tokenizer(self, vocab_size=VOCAB_SIZE):
        tokenizer = BPETokenizer(vocab_size)
        rows = self.connection.execute(
            "SELECT left_token,right_token,merged_token FROM tokenizer_merges ORDER BY rank"
        ).fetchall()
        if rows:
            tokenizer.load_merges([(row[0], row[1], row[2]) for row in rows])
        return tokenizer

    def training_samples(self, limit=1000):
        rows = self.connection.execute(
            "SELECT task,input_text,target_text,observation_json,action,reward FROM training_samples ORDER BY RANDOM() LIMIT ?",
            (int(limit),)
        ).fetchall()
        return [dict(row) for row in rows]

    def set_metadata(self, key, value):
        self.connection.execute(
            "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)",
            (str(key), str(value))
        )
        self.connection.commit()

    def close(self):
        self.connection.close()


class ResidualAttentionLayer(nn.Module):
    def __init__(self, hidden_size=HIDDEN_SIZE, heads=NUM_HEADS, dropout=0.1):
        super().__init__()
        self.norm_attention = nn.LayerNorm(hidden_size)
        self.attention = nn.MultiheadAttention(
            hidden_size, heads, dropout=dropout, batch_first=True
        )
        self.norm_feedforward = nn.LayerNorm(hidden_size)
        self.feedforward = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, hidden_size),
            nn.Dropout(dropout)
        )

    def forward(self, values, causal_mask=None):
        normalized = self.norm_attention(values)
        attended, _ = self.attention(
            normalized,
            normalized,
            normalized,
            attn_mask=causal_mask,
            need_weights=False
        )
        values = values + attended
        return values + self.feedforward(self.norm_feedforward(values))


class UniversalNeuralNetwork(nn.Module):
    def __init__(
        self,
        vocab_size=VOCAB_SIZE,
        hidden_size=HIDDEN_SIZE,
        num_layers=NUM_LAYERS,
        num_heads=NUM_HEADS,
        max_sequence=MAX_SEQUENCE,
        num_actions=NUM_ACTIONS
    ):
        super().__init__()
        self.hidden_size = hidden_size
        self.max_sequence = max_sequence
        self.num_actions = num_actions
        self.token_embedding = nn.Embedding(vocab_size, hidden_size)
        self.position_embedding = nn.Embedding(max_sequence, hidden_size)
        self.game_projection = nn.Linear(hidden_size, hidden_size)
        self.layers = nn.ModuleList([
            ResidualAttentionLayer(hidden_size, num_heads)
            for _ in range(num_layers)
        ])
        self.final_norm = nn.LayerNorm(hidden_size)
        self.language_head = nn.Linear(hidden_size, vocab_size, bias=False)
        self.language_head.weight = self.token_embedding.weight
        self.game_action_head = nn.Linear(hidden_size, num_actions)
        self.game_value_head = nn.Linear(hidden_size, 1)
        self.apply(self._initialize)

    @staticmethod
    def _initialize(module):
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def run_layers(self, values, causal=True):
        sequence_length = values.shape[1]
        mask = None
        if causal and sequence_length > 1:
            mask = torch.triu(
                torch.ones(sequence_length, sequence_length, device=values.device, dtype=torch.bool),
                diagonal=1
            )
        for layer in self.layers:
            values = layer(values, mask)
        return self.final_norm(values)

    def forward_chat(self, token_ids):
        sequence_length = token_ids.shape[1]
        if sequence_length > self.max_sequence:
            token_ids = token_ids[:, -self.max_sequence:]
            sequence_length = self.max_sequence
        positions = torch.arange(sequence_length, device=token_ids.device).unsqueeze(0)
        values = self.token_embedding(token_ids) + self.position_embedding(positions)
        hidden = self.run_layers(values, causal=True)
        return self.language_head(hidden)

    def forward_game(self, feature_vectors):
        if feature_vectors.ndim == 1:
            feature_vectors = feature_vectors.unsqueeze(0)
        values = self.game_projection(feature_vectors).unsqueeze(1)
        hidden = self.run_layers(values, causal=False)[:, 0, :]
        return self.game_action_head(hidden), self.game_value_head(hidden).squeeze(-1)


def hashed_index(value, size):
    digest = hashlib.blake2b(str(value).encode("utf-8"), digest_size=8).digest()
    number = int.from_bytes(digest, "little")
    return number % size, (1.0 if number & 1 else -1.0)


def encode_game_observation(observation, size=HIDDEN_SIZE):
    features = [0.0] * size

    def add_feature(key, value):
        index, sign = hashed_index(key, size)
        if isinstance(value, bool):
            amount = 1.0 if value else -1.0
        elif isinstance(value, (int, float)):
            amount = math.tanh(float(value) / 1000.0)
        else:
            amount = 1.0
        features[index] += sign * amount

    def walk(value, prefix="state"):
        if isinstance(value, dict):
            for key, item in value.items():
                walk(item, prefix + "." + str(key))
        elif isinstance(value, (list, tuple)):
            for index, item in enumerate(value):
                walk(item, prefix + "[" + str(index) + "]")
        elif isinstance(value, (int, float, bool)):
            add_feature(prefix, value)
        elif value is not None:
            text = str(value).lower()
            add_feature(prefix, text)
            for token in text.split()[:128]:
                add_feature(prefix + ":" + token, token)

    walk(observation)
    features = [math.tanh(value) for value in features]
    return torch.tensor(features, dtype=torch.float32)


def action_to_index(action, num_actions=NUM_ACTIONS):
    digest = hashlib.blake2s(str(action).encode("utf-8"), digest_size=4).digest()
    return int.from_bytes(digest, "little") % num_actions


def choose_device():
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def build_tokenizer(memory):
    tokenizer = memory.load_tokenizer(VOCAB_SIZE)
    if not tokenizer.merges:
        tokenizer.train(memory.corpus())
        memory.save_tokenizer(tokenizer)
    return tokenizer


def create_model(device):
    model = UniversalNeuralNetwork()
    return model.to(device)


def save_checkpoint(model, path, step=0):
    torch.save(
        {
            "model": model.state_dict(),
            "config": {
                "vocab_size": VOCAB_SIZE,
                "hidden_size": HIDDEN_SIZE,
                "num_layers": NUM_LAYERS,
                "num_heads": NUM_HEADS,
                "max_sequence": MAX_SEQUENCE,
                "num_actions": NUM_ACTIONS
            },
            "step": int(step)
        },
        path
    )


def load_model(path, device):
    if not os.path.exists(path):
        raise FileNotFoundError("Checkpoint not found. Run the init command first.")
    checkpoint = torch.load(path, map_location=device, weights_only=True)
    config = checkpoint.get("config", {})
    model = UniversalNeuralNetwork(
        vocab_size=config.get("vocab_size", VOCAB_SIZE),
        hidden_size=config.get("hidden_size", HIDDEN_SIZE),
        num_layers=config.get("num_layers", NUM_LAYERS),
        num_heads=config.get("num_heads", NUM_HEADS),
        max_sequence=config.get("max_sequence", MAX_SEQUENCE),
        num_actions=config.get("num_actions", NUM_ACTIONS)
    ).to(device)
    model.load_state_dict(checkpoint["model"])
    return model, int(checkpoint.get("step", 0))


def generate_text(model, tokenizer, prompt, device, max_new_tokens=80, temperature=0.8, top_k=40):
    model.eval()
    token_ids = tokenizer.encode(prompt, special_tokens=False)
    token_ids = [SPECIAL_BOS] + token_ids
    generated = []
    with torch.no_grad():
        for _ in range(max_new_tokens):
            context = token_ids[-MAX_SEQUENCE:]
            inputs = torch.tensor([context], dtype=torch.long, device=device)
            logits = model.forward_chat(inputs)[0, -1, :tokenizer.active_vocab_size]
            logits = logits / max(float(temperature), 1e-5)
            if top_k > 0 and top_k < logits.numel():
                threshold = torch.topk(logits, top_k).values[-1]
                logits[logits < threshold] = -float("inf")
            probabilities = F.softmax(logits, dim=-1)
            next_id = int(torch.multinomial(probabilities, 1).item())
            if next_id == SPECIAL_EOS:
                break
            if next_id in (SPECIAL_BOS, SPECIAL_PAD):
                continue
            token_ids.append(next_id)
            generated.append(next_id)
    return tokenizer.decode(generated)


def train_model(model, tokenizer, memory, device, steps=10, sample_limit=1000, learning_rate=2e-5):
    samples = memory.training_samples(sample_limit)
    if not samples:
        raise RuntimeError("No observations available. Add chat or gameplay examples before training.")
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=0.01)
    model.train()
    losses = []
    for step in range(steps):
        sample = random.choice(samples)
        optimizer.zero_grad(set_to_none=True)
        if sample["task"] == "chat":
            text = sample["input_text"] + "\n" + sample["target_text"]
            ids = tokenizer.encode(text)
            ids = ids[:MAX_SEQUENCE + 1]
            if len(ids) < 2:
                continue
            inputs = torch.tensor([ids[:-1]], dtype=torch.long, device=device)
            targets = torch.tensor([ids[1:]], dtype=torch.long, device=device)
            logits = model.forward_chat(inputs)
            loss = F.cross_entropy(
                logits.reshape(-1, logits.shape[-1]),
                targets.reshape(-1)
            )
        else:
            try:
                observation = json.loads(sample["observation_json"])
            except json.JSONDecodeError:
                continue
            features = encode_game_observation(observation).to(device)
            actions, value = model.forward_game(features)
            action_id = torch.tensor(
                [action_to_index(sample["action"])],
                dtype=torch.long,
                device=device
            )
            reward = torch.tensor(
                [max(-1.0, min(1.0, float(sample["reward"])))],
                dtype=torch.float32,
                device=device
            )
            loss = F.cross_entropy(actions, action_id) + 0.25 * F.mse_loss(value, reward)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        losses.append(float(loss.detach().cpu()))
        if (step + 1) % 1 == 0:
            print(json.dumps({
                "step": step + 1,
                "loss": round(losses[-1], 6),
                "task": sample["task"]
            }))
    return sum(losses) / max(1, len(losses))


def initialize(args, memory, device):
    tokenizer = build_tokenizer(memory)
    model = create_model(device)
    save_checkpoint(model, args.checkpoint, 0)
    print(json.dumps({
        "status": "initialized",
        "checkpoint": args.checkpoint,
        "database": args.db,
        "layers": NUM_LAYERS,
        "neurons_per_layer": HIDDEN_SIZE,
        "active_tokens": tokenizer.active_vocab_size,
        "parameters": sum(parameter.numel() for parameter in model.parameters()),
        "device": str(device)
    }, indent=2))


def run_chat(args, memory, tokenizer, device):
    model, _ = load_model(args.checkpoint, device)
    recent = memory.recent_events(4)
    context = []
    for event in recent:
        try:
            payload = json.loads(event["payload"])
        except json.JSONDecodeError:
            continue
        context.append("[" + event["kind"].upper() + "] " + json.dumps(payload, ensure_ascii=False))
    full_prompt = "\n".join(context + ["[USER] " + args.prompt, "[ASSISTANT]"])
    response = generate_text(
        model,
        tokenizer,
        full_prompt,
        device,
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
        top_k=args.top_k
    )
    memory.log_event("chat_inference", {"prompt": args.prompt, "response": response})
    print(response)


def run_game_action(args, memory, device):
    observation = json.loads(args.observation)
    model, _ = load_model(args.checkpoint, device)
    model.eval()
    features = encode_game_observation(observation).to(device)
    with torch.no_grad():
        logits, value = model.forward_game(features)
        probabilities = F.softmax(logits[0], dim=-1)
    candidates = json.loads(args.actions) if args.actions else []
    if candidates:
        ranked = []
        for action in candidates:
            ranked.append((float(probabilities[action_to_index(action)].item()), action))
        score, selected = max(ranked, key=lambda item: item[0])
    else:
        index = int(torch.argmax(probabilities).item())
        score = float(probabilities[index].item())
        selected = index
    memory.log_event("game_prediction", {
        "observation": observation,
        "selected_action": selected,
        "confidence": score,
        "estimated_value": float(value[0].item())
    })
    print(json.dumps({
        "action": selected,
        "confidence": round(score, 6),
        "estimated_value": round(float(value[0].item()), 6)
    }, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(
        description="14-layer universal neural core for chat and gameplay observations."
    )
    parser.add_argument("--db", default="universal_neural_memory.sqlite3")
    parser.add_argument("--checkpoint", default="universal_neural_core.pt")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("init")

    chat_parser = commands.add_parser("observe-chat")
    chat_parser.add_argument("--prompt", required=True)
    chat_parser.add_argument("--response", required=True)

    game_parser = commands.add_parser("observe-game")
    game_parser.add_argument("--observation", required=True)
    game_parser.add_argument("--action", default="")
    game_parser.add_argument("--reward", type=float, default=0.0)

    train_parser = commands.add_parser("train")
    train_parser.add_argument("--steps", type=int, default=10)
    train_parser.add_argument("--limit", type=int, default=1000)
    train_parser.add_argument("--learning-rate", type=float, default=2e-5)

    chat_run_parser = commands.add_parser("chat")
    chat_run_parser.add_argument("--prompt", required=True)
    chat_run_parser.add_argument("--max-new-tokens", type=int, default=80)
    chat_run_parser.add_argument("--temperature", type=float, default=0.8)
    chat_run_parser.add_argument("--top-k", type=int, default=40)

    game_run_parser = commands.add_parser("act")
    game_run_parser.add_argument("--observation", required=True)
    game_run_parser.add_argument("--actions", default="[]")

    args = parser.parse_args()
    torch.set_num_threads(max(1, min(8, os.cpu_count() or 1)))
    device = choose_device()
    memory = SQLMemory(args.db)
    try:
        if args.command == "init":
            initialize(args, memory, device)
        elif args.command == "observe-chat":
            memory.record_chat(args.prompt, args.response)
            print("Chat observation stored.")
        elif args.command == "observe-game":
            observation = json.loads(args.observation)
            memory.record_game(observation, args.action, args.reward)
            print("Gameplay observation stored.")
        elif args.command == "train":
            tokenizer = build_tokenizer(memory)
            model, previous_step = load_model(args.checkpoint, device)
            average_loss = train_model(
                model,
                tokenizer,
                memory,
                device,
                steps=max(1, args.steps),
                sample_limit=max(1, args.limit),
                learning_rate=args.learning_rate
            )
            save_checkpoint(model, args.checkpoint, previous_step + max(1, args.steps))
            print(json.dumps({
                "status": "trained",
                "average_loss": round(average_loss, 6),
                "total_steps": previous_step + max(1, args.steps),
                "checkpoint": args.checkpoint
            }, indent=2))
        elif args.command == "chat":
            tokenizer = build_tokenizer(memory)
            run_chat(args, memory, tokenizer, device)
        elif args.command == "act":
            run_game_action(args, memory, device)
    finally:
        memory.close()


if __name__ == "__main__":
    main()
