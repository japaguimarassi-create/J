import argparse
import json
import math
import random
import re
import sqlite3
import time
from collections import Counter
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F


MODEL_WIDTH = 1024
MODEL_LAYERS = 14
MODEL_HEADS = 16
FEED_FORWARD_WIDTH = 4096
MAX_SEQUENCE = 256
STATE_WIDTH = 256
ACTION_COUNT = 64
CONTINUOUS_ACTIONS = 8
SPECIAL_TOKENS = ["<pad>", "<unk>", "<bos>", "<eos>", "<chat>", "<game>"]


class NeuralTokenizer:
    def __init__(self, vocab_size=8192):
        self.vocab_size = vocab_size
        self.token_to_id = {token: index for index, token in enumerate(SPECIAL_TOKENS)}
        self.id_to_token = list(SPECIAL_TOKENS)

    def fit(self, texts):
        counts = Counter()
        for text in texts:
            counts.update(self._split(text))
        for token, _ in counts.most_common(max(0, self.vocab_size - len(SPECIAL_TOKENS))):
            if token not in self.token_to_id:
                self.token_to_id[token] = len(self.id_to_token)
                self.id_to_token.append(token)
        return self

    def _split(self, text):
        return re.findall(r"\w+|[^\w\s]", str(text).lower(), flags=re.UNICODE)

    def encode(self, text, max_length=MAX_SEQUENCE):
        ids = [self.token_to_id["<bos>"]]
        ids.extend(self.token_to_id.get(token, self.token_to_id["<unk>"]) for token in self._split(text))
        ids.append(self.token_to_id["<eos>"])
        return ids[:max_length]

    def decode(self, ids):
        ignored = {"<pad>", "<bos>", "<eos>", "<chat>", "<game>"}
        return " ".join(
            self.id_to_token[index] if 0 <= int(index) < len(self.id_to_token) else "<unk>"
            for index in ids
            if (self.id_to_token[index] if 0 <= int(index) < len(self.id_to_token) else "<unk>") not in ignored
        )

    def save(self, connection):
        connection.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES('tokenizer_vocab', ?)",
            (json.dumps(self.id_to_token, ensure_ascii=False),)
        )

    @classmethod
    def load(cls, connection, vocab_size=8192):
        tokenizer = cls(vocab_size)
        row = connection.execute(
            "SELECT value FROM metadata WHERE key='tokenizer_vocab'"
        ).fetchone()
        if row:
            tokenizer.id_to_token = json.loads(row[0])
            tokenizer.token_to_id = {token: index for index, token in enumerate(tokenizer.id_to_token)}
        return tokenizer


class SQLMemory:
    def __init__(self, path="universal_neural_memory.sqlite3"):
        self.path = str(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=NORMAL")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS observations(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mode TEXT NOT NULL,
                input_data TEXT NOT NULL,
                target_data TEXT,
                reward REAL DEFAULT 0,
                terminal INTEGER DEFAULT 0,
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS episodes(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mode TEXT NOT NULL,
                summary TEXT,
                total_reward REAL DEFAULT 0,
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS metadata(
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_observations_mode ON observations(mode);
            CREATE INDEX IF NOT EXISTS idx_observations_time ON observations(created_at);
        """)
        self.connection.commit()

    def add(self, mode, input_data, target_data=None, reward=0.0, terminal=False):
        self.connection.execute(
            "INSERT INTO observations(mode,input_data,target_data,reward,terminal,created_at) VALUES(?,?,?,?,?,?)",
            (mode, json.dumps(input_data, ensure_ascii=False), json.dumps(target_data, ensure_ascii=False),
             float(reward), int(terminal), time.time())
        )
        self.connection.commit()

    def sample(self, mode, limit=128):
        rows = self.connection.execute(
            "SELECT input_data,target_data,reward,terminal FROM observations WHERE mode=? ORDER BY RANDOM() LIMIT ?",
            (mode, int(limit))
        ).fetchall()
        return [
            {"input": json.loads(row[0]), "target": json.loads(row[1]) if row[1] else None,
             "reward": row[2], "terminal": bool(row[3])}
            for row in rows
        ]

    def count(self, mode=None):
        if mode:
            return self.connection.execute(
                "SELECT COUNT(*) FROM observations WHERE mode=?", (mode,)
            ).fetchone()[0]
        return self.connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0]

    def close(self):
        self.connection.commit()
        self.connection.close()


class ProceduralObserver:
    def __init__(self, seed=None):
        self.random = random.Random(seed)

    def chat(self, text):
        text = str(text).strip()
        variants = [text]
        if text:
            variants.append(re.sub(r"\s+", " ", text))
            variants.append(text.lower())
        return {"text": self.random.choice(variants), "length": len(text), "source": "chat"}

    def game(self, state, frame=None, noise=0.01):
        values = torch.as_tensor(state, dtype=torch.float32).flatten()
        if values.numel() < STATE_WIDTH:
            values = F.pad(values, (0, STATE_WIDTH - values.numel()))
        values = values[:STATE_WIDTH]
        if noise > 0:
            values = values + torch.randn_like(values) * float(noise)
        result = {"state": values.clamp(-10, 10).tolist(), "source": "game"}
        if frame is not None:
            result["frame_shape"] = list(torch.as_tensor(frame).shape)
        return result


class VisualEncoder(nn.Module):
    def __init__(self, output_width=MODEL_WIDTH):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Conv2d(3, 64, 5, stride=2, padding=2),
            nn.GELU(),
            nn.Conv2d(64, 128, 3, stride=2, padding=1),
            nn.GroupNorm(8, 128),
            nn.GELU(),
            nn.Conv2d(128, 256, 3, stride=2, padding=1),
            nn.GroupNorm(16, 256),
            nn.GELU(),
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(256, output_width),
            nn.LayerNorm(output_width)
        )

    def forward(self, frames):
        if frames.dtype == torch.uint8:
            frames = frames.float() / 255.0
        else:
            frames = frames.float()
        return self.layers(frames)


class UniversalNeuralNetwork(nn.Module):
    def __init__(self, vocab_size=8192, dropout=0.1):
        super().__init__()
        self.width = MODEL_WIDTH
        self.token_embedding = nn.Embedding(vocab_size, MODEL_WIDTH, padding_idx=0)
        self.state_encoder = nn.Sequential(
            nn.Linear(STATE_WIDTH, MODEL_WIDTH),
            nn.LayerNorm(MODEL_WIDTH),
            nn.GELU(),
            nn.Linear(MODEL_WIDTH, MODEL_WIDTH)
        )
        self.visual_encoder = VisualEncoder()
        self.mode_embedding = nn.Embedding(2, MODEL_WIDTH)
        self.position_embedding = nn.Embedding(MAX_SEQUENCE, MODEL_WIDTH)
        block = nn.TransformerEncoderLayer(
            d_model=MODEL_WIDTH,
            nhead=MODEL_HEADS,
            dim_feedforward=FEED_FORWARD_WIDTH,
            dropout=dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True
        )
        self.backbone = nn.TransformerEncoder(
            block,
            num_layers=MODEL_LAYERS,
            norm=nn.LayerNorm(MODEL_WIDTH),
            enable_nested_tensor=False
        )
        self.chat_head = nn.Linear(MODEL_WIDTH, vocab_size, bias=False)
        self.chat_head.weight = self.token_embedding.weight
        self.action_head = nn.Sequential(
            nn.LayerNorm(MODEL_WIDTH),
            nn.Linear(MODEL_WIDTH, MODEL_WIDTH),
            nn.GELU(),
            nn.Linear(MODEL_WIDTH, ACTION_COUNT)
        )
        self.continuous_head = nn.Sequential(
            nn.LayerNorm(MODEL_WIDTH),
            nn.Linear(MODEL_WIDTH, MODEL_WIDTH // 2),
            nn.GELU(),
            nn.Linear(MODEL_WIDTH // 2, CONTINUOUS_ACTIONS),
            nn.Tanh()
        )
        self.value_head = nn.Linear(MODEL_WIDTH, 1)
        self.reward_head = nn.Linear(MODEL_WIDTH, 1)
        self.terminal_head = nn.Linear(MODEL_WIDTH, 1)

    def _encode(self, embeddings, mode_id, causal=True):
        batch, length, _ = embeddings.shape
        positions = torch.arange(length, device=embeddings.device).unsqueeze(0)
        mode = torch.full((batch, length), mode_id, device=embeddings.device, dtype=torch.long)
        hidden = embeddings + self.position_embedding(positions) + self.mode_embedding(mode)
        mask = torch.triu(
            torch.ones(length, length, device=hidden.device, dtype=torch.bool), diagonal=1
        ) if causal and length > 1 else None
        return self.backbone(hidden, mask=mask)

    def observe_chat(self, token_ids):
        hidden = self._encode(self.token_embedding(token_ids), 0, causal=True)
        return {"logits": self.chat_head(hidden), "hidden": hidden}

    def observe_game(self, state, frames=None):
        if state.ndim == 2:
            state = state.unsqueeze(1)
        state_features = self.state_encoder(state.float())
        if frames is not None:
            if frames.ndim == 4:
                frames = frames.unsqueeze(1)
            batch, steps = frames.shape[:2]
            visual = self.visual_encoder(frames.reshape(batch * steps, *frames.shape[2:]))
            visual = visual.reshape(batch, steps, MODEL_WIDTH)
            state_features = state_features + visual
        hidden = self._encode(state_features, 1, causal=True)
        return {
            "action_logits": self.action_head(hidden),
            "continuous_actions": self.continuous_head(hidden),
            "value": self.value_head(hidden),
            "reward": self.reward_head(hidden),
            "terminal_logits": self.terminal_head(hidden),
            "hidden": hidden
        }

    def forward(self, mode, **inputs):
        if mode == "chat":
            return self.observe_chat(inputs["token_ids"])
        if mode == "game":
            return self.observe_game(inputs["state"], inputs.get("frames"))
        raise ValueError("mode must be 'chat' or 'game'")

    @torch.no_grad()
    def choose_action(self, state, frames=None, threshold=0.5):
        self.eval()
        output = self.observe_game(state, frames)
        logits = output["action_logits"][:, -1]
        return {
            "buttons": (torch.sigmoid(logits) >= threshold).int(),
            "button_probabilities": torch.sigmoid(logits),
            "continuous": output["continuous_actions"][:, -1],
            "value": output["value"][:, -1],
            "predicted_reward": output["reward"][:, -1],
            "terminal_probability": torch.sigmoid(output["terminal_logits"][:, -1])
        }


def count_parameters(model):
    return sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)


def train_chat_step(model, optimizer, token_ids):
    model.train()
    optimizer.zero_grad(set_to_none=True)
    output = model.observe_chat(token_ids[:, :-1])
    loss = F.cross_entropy(
        output["logits"].reshape(-1, output["logits"].size(-1)),
        token_ids[:, 1:].reshape(-1),
        ignore_index=0
    )
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    optimizer.step()
    return float(loss.detach())


def train_game_step(model, optimizer, state, action_targets, rewards, terminal_targets):
    model.train()
    optimizer.zero_grad(set_to_none=True)
    output = model.observe_game(state)
    action_loss = F.binary_cross_entropy_with_logits(
        output["action_logits"][:, -1], action_targets.float()
    )
    reward_loss = F.smooth_l1_loss(output["reward"][:, -1].squeeze(-1), rewards.float())
    terminal_loss = F.binary_cross_entropy_with_logits(
        output["terminal_logits"][:, -1].squeeze(-1), terminal_targets.float()
    )
    loss = action_loss + reward_loss + terminal_loss
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    optimizer.step()
    return {
        "loss": float(loss.detach()),
        "action_loss": float(action_loss.detach()),
        "reward_loss": float(reward_loss.detach()),
        "terminal_loss": float(terminal_loss.detach())
    }


def save_checkpoint(model, tokenizer, path, optimizer=None):
    payload = {
        "model": model.state_dict(),
        "tokenizer": tokenizer.id_to_token,
        "architecture": {
            "layers": MODEL_LAYERS,
            "width": MODEL_WIDTH,
            "heads": MODEL_HEADS,
            "feed_forward": FEED_FORWARD_WIDTH
        }
    }
    if optimizer is not None:
        payload["optimizer"] = optimizer.state_dict()
    torch.save(payload, path)


def load_checkpoint(path, device="cpu"):
    payload = torch.load(path, map_location=device, weights_only=False)
    tokenizer = NeuralTokenizer(vocab_size=len(payload["tokenizer"]))
    tokenizer.id_to_token = payload["tokenizer"]
    tokenizer.token_to_id = {token: index for index, token in enumerate(tokenizer.id_to_token)}
    model = UniversalNeuralNetwork(vocab_size=len(tokenizer.id_to_token)).to(device)
    model.load_state_dict(payload["model"])
    return model, tokenizer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default="universal_neural_memory.sqlite3")
    parser.add_argument("--checkpoint", default="universal_neural_network.pt")
    parser.add_argument("--vocab-size", type=int, default=8192)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--initialize", action="store_true")
    args = parser.parse_args()

    memory = SQLMemory(args.database)
    tokenizer = NeuralTokenizer.load(memory.connection, args.vocab_size)
    if args.initialize or not Path(args.checkpoint).exists():
        model = UniversalNeuralNetwork(vocab_size=args.vocab_size).to(args.device)
        tokenizer.fit([
            "Observe the environment, predict the next state, and choose an action.",
            "Analyze the player's position, health, inventory, objective, and nearby threats.",
            "Respond clearly, use context, remember relevant observations, and avoid inventing facts."
        ])
        tokenizer.save(memory.connection)
        save_checkpoint(model, tokenizer, args.checkpoint)
    else:
        model, tokenizer = load_checkpoint(args.checkpoint, args.device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=0.01)
    print(json.dumps({
        "status": "initialized",
        "layers": MODEL_LAYERS,
        "neurons_per_layer": MODEL_WIDTH,
        "attention_heads": MODEL_HEADS,
        "parameters": count_parameters(model),
        "device": args.device,
        "database": args.database,
        "checkpoint": args.checkpoint,
        "chat_observations": memory.count("chat"),
        "game_observations": memory.count("game"),
        "trained": False
    }, indent=2))
    memory.close()


if __name__ == "__main__":
    main()
