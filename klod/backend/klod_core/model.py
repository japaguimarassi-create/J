import torch
from torch import nn
from torch.nn import functional as F

def apply_rope(x):
    length, dim = x.shape[-2:]
    if dim % 2:
        raise ValueError("attention head dimension must be even")
    pos = torch.arange(length, device=x.device, dtype=torch.float32)
    freq = 1.0 / (10000 ** (torch.arange(0, dim, 2, device=x.device).float() / dim))
    angle = torch.outer(pos, freq)
    cos, sin = angle.cos()[None, None], angle.sin()[None, None]
    even, odd = x[..., 0::2], x[..., 1::2]
    return torch.stack((even * cos - odd * sin, even * sin + odd * cos), dim=-1).flatten(-2)

class Attention(nn.Module):
    def __init__(self, width, heads):
        super().__init__()
        if width % heads or (width // heads) % 2:
            raise ValueError("width must divide into even-sized heads")
        self.heads, self.head_dim = heads, width // heads
        self.qkv = nn.Linear(width, width * 3, bias=False)
        self.proj = nn.Linear(width, width, bias=False)

    def forward(self, x):
        b, n, width = x.shape
        q, k, v = self.qkv(x).chunk(3, dim=-1)
        def split(t):
            return t.view(b, n, self.heads, self.head_dim).transpose(1, 2)
        q, k, v = split(q), split(k), split(v)
        q, k = apply_rope(q), apply_rope(k)
        mask = torch.ones(n, n, device=x.device, dtype=torch.bool).tril()
        out = F.scaled_dot_product_attention(q, k, v, attn_mask=mask)
        return self.proj(out.transpose(1, 2).contiguous().view(b, n, width))

class Block(nn.Module):
    def __init__(self, width, heads, expansion):
        super().__init__()
        self.norm1, self.attn = nn.LayerNorm(width), Attention(width, heads)
        self.norm2 = nn.LayerNorm(width)
        self.gate = nn.Linear(width, expansion * 2, bias=False)
        self.down = nn.Linear(expansion, width, bias=False)

    def forward(self, x):
        x = x + self.attn(self.norm1(x))
        gate, value = self.gate(self.norm2(x)).chunk(2, dim=-1)
        return x + self.down(F.silu(gate) * value)

class KlodLM(nn.Module):
    def __init__(self, vocab_size, width=128, layers=4, heads=4, expansion=256):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, width)
        self.blocks = nn.ModuleList([Block(width, heads, expansion) for _ in range(layers)])
        self.norm = nn.LayerNorm(width)
        self.output = nn.Linear(width, vocab_size, bias=False)
        self.output.weight = self.embedding.weight

    def forward(self, tokens, targets=None):
        x = self.embedding(tokens)
        for block in self.blocks:
            x = block(x)
        logits = self.output(self.norm(x))
        loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)), targets.reshape(-1)) if targets is not None else None
        return logits, loss

    @property
    def parameter_count(self):
        return sum(p.numel() for p in self.parameters())
