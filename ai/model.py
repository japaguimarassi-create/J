import torch
from torch import nn

VOCAB_SIZE = 258
BOS_ID = 256
EOS_ID = 257
D_MODEL = 48
N_HEADS = 4
N_LAYERS = 12
FF_DIM = 92
MAX_SEQ_LEN = 256


class CausalSelfAttention(nn.Module):
    def __init__(self):
        super().__init__()
        self.qkv = nn.Linear(D_MODEL, D_MODEL * 3)
        self.proj = nn.Linear(D_MODEL, D_MODEL)
        self.n_heads = N_HEADS
        self.head_dim = D_MODEL // N_HEADS

    def forward(self, x):
        batch, seq_len, width = x.shape
        q, k, v = self.qkv(x).chunk(3, dim=-1)
        q = q.view(batch, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        k = k.view(batch, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        v = v.view(batch, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        blocked = torch.ones(seq_len, seq_len, device=x.device, dtype=torch.bool).triu(1)
        attended = torch.nn.functional.scaled_dot_product_attention(q, k, v, attn_mask=~blocked)
        attended = attended.transpose(1, 2).contiguous().view(batch, seq_len, width)
        return self.proj(attended)


class TransformerBlock(nn.Module):
    def __init__(self):
        super().__init__()
        self.ln1 = nn.LayerNorm(D_MODEL)
        self.attention = CausalSelfAttention()
        self.ln2 = nn.LayerNorm(D_MODEL)
        self.feed_forward = nn.Sequential(
            nn.Linear(D_MODEL, FF_DIM),
            nn.GELU(),
            nn.Linear(FF_DIM, D_MODEL),
        )

    def forward(self, x):
        x = x + self.attention(self.ln1(x))
        return x + self.feed_forward(self.ln2(x))


class ForgeStudent(nn.Module):
    def __init__(self):
        super().__init__()
        self.token_embedding = nn.Embedding(VOCAB_SIZE, D_MODEL)
        self.position_embedding = nn.Embedding(MAX_SEQ_LEN, D_MODEL)
        self.blocks = nn.ModuleList(TransformerBlock() for _ in range(N_LAYERS))
        self.final_norm = nn.LayerNorm(D_MODEL)
        self.output_bias = nn.Parameter(torch.zeros(VOCAB_SIZE))

    def forward(self, tokens):
        _, seq_len = tokens.shape
        if seq_len > MAX_SEQ_LEN:
            tokens = tokens[:, -MAX_SEQ_LEN:]
            seq_len = tokens.shape[1]
        positions = torch.arange(seq_len, device=tokens.device)
        x = self.token_embedding(tokens) + self.position_embedding(positions)[None, :, :]
        for block in self.blocks:
            x = block(x)
        return torch.nn.functional.linear(self.final_norm(x), self.token_embedding.weight, self.output_bias)

    @staticmethod
    def parameter_count():
        return sum(parameter.numel() for parameter in ForgeStudent().parameters())


def encode(text, add_bos=True, add_eos=False):
    ids = list(text.encode("utf-8", errors="replace"))
    if add_bos:
        ids.insert(0, BOS_ID)
    if add_eos:
        ids.append(EOS_ID)
    return ids


def decode(token_ids):
    return bytes(token for token in token_ids if 0 <= token <= 255).decode("utf-8", errors="replace")


def generate(model, prompt, max_new_tokens=120, temperature=0.8, device="cpu"):
    model.eval()
    prefix = encode(prompt)
    generated = prefix[:]
    with torch.no_grad():
        for _ in range(max_new_tokens):
            context = torch.tensor([generated[-MAX_SEQ_LEN:]], dtype=torch.long, device=device)
            logits = model(context)[0, -1] / max(temperature, 0.05)
            logits[BOS_ID] = float("-inf")
            next_id = int(torch.multinomial(torch.softmax(logits, dim=-1), 1).item())
            if next_id == EOS_ID:
                break
            generated.append(next_id)
    return decode(generated[len(prefix):]).strip()
