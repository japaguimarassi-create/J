import torch
import torch.nn as nn
import torch.nn.functional as F


class ResidualBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, 3, stride=stride, padding=1, bias=False)
        self.norm1 = nn.GroupNorm(8, out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, 3, padding=1, bias=False)
        self.norm2 = nn.GroupNorm(8, out_channels)
        self.shortcut = nn.Identity()
        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, 1, stride=stride, bias=False),
                nn.GroupNorm(8, out_channels)
            )

    def forward(self, x):
        residual = self.shortcut(x)
        x = F.gelu(self.norm1(self.conv1(x)))
        x = self.norm2(self.conv2(x))
        return F.gelu(x + residual)


class VisualEncoder(nn.Module):
    def __init__(self, output_dim=512):
        super().__init__()
        self.network = nn.Sequential(
            nn.Conv2d(3, 64, 5, stride=2, padding=2),
            nn.GroupNorm(8, 64),
            nn.GELU(),
            nn.MaxPool2d(2),
            ResidualBlock(64, 128, 2),
            ResidualBlock(128, 256, 2),
            ResidualBlock(256, 512, 2),
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(512, output_dim),
            nn.LayerNorm(output_dim)
        )

    def forward(self, x):
        return self.network(x)


class UniversalGameNet(nn.Module):
    def __init__(
        self,
        state_dim=128,
        num_buttons=32,
        continuous_dim=4,
        d_model=512,
        num_layers=12,
        num_heads=8,
        max_seq_len=128,
        dropout=0.1
    ):
        super().__init__()
        self.state_dim = state_dim
        self.max_seq_len = max_seq_len
        self.visual_encoder = VisualEncoder(512)
        self.visual_projection = nn.Sequential(
            nn.Linear(512, d_model),
            nn.LayerNorm(d_model),
            nn.GELU()
        )
        self.state_encoder = nn.Sequential(
            nn.Linear(state_dim, d_model),
            nn.LayerNorm(d_model),
            nn.GELU(),
            nn.Linear(d_model, d_model),
            nn.LayerNorm(d_model)
        ) if state_dim > 0 else None
        self.fusion = nn.Sequential(
            nn.Linear(d_model * 2, d_model),
            nn.LayerNorm(d_model),
            nn.GELU()
        )
        self.position_embedding = nn.Parameter(torch.randn(1, max_seq_len, d_model) * 0.02)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=num_heads,
            dim_feedforward=d_model * 4,
            dropout=dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True
        )
        self.transformer = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers,
            norm=nn.LayerNorm(d_model)
        )
        self.memory_gate = nn.Sequential(
            nn.Linear(d_model * 2, d_model),
            nn.Sigmoid()
        )
        self.button_head = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.GELU(),
            nn.Linear(d_model, num_buttons)
        )
        self.continuous_head = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.GELU(),
            nn.Linear(d_model, continuous_dim),
            nn.Tanh()
        )
        self.value_head = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.GELU(),
            nn.Linear(d_model // 2, 1)
        )
        self.reward_head = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.GELU(),
            nn.Linear(d_model // 2, 1)
        )
        self.done_head = nn.Linear(d_model, 1)
        self.world_model = nn.Sequential(
            nn.Linear(d_model, d_model * 2),
            nn.GELU(),
            nn.Linear(d_model * 2, d_model),
            nn.LayerNorm(d_model)
        )

    def forward(self, frames, state=None, causal=True):
        if frames.ndim == 4:
            frames = frames.unsqueeze(1)
        if frames.ndim != 5:
            raise ValueError("frames must have shape [B,T,C,H,W]")
        batch, seq_len, channels, height, width = frames.shape
        if channels != 3:
            raise ValueError("Expected RGB frames with 3 channels")
        if seq_len > self.max_seq_len:
            raise ValueError("Sequence exceeds max_seq_len")
        if frames.dtype == torch.uint8:
            frames = frames.float() / 255.0
        else:
            frames = frames.float()
        frames = frames.reshape(batch * seq_len, channels, height, width)
        visual_features = self.visual_encoder(frames)
        visual_features = visual_features.reshape(batch, seq_len, -1)
        visual_features = self.visual_projection(visual_features)
        if self.state_encoder is not None:
            if state is None:
                state_features = torch.zeros_like(visual_features)
            else:
                if state.ndim == 2:
                    state = state.unsqueeze(1)
                if state.shape != (batch, seq_len, self.state_dim):
                    raise ValueError("Invalid state dimensions")
                state_features = self.state_encoder(state.float())
        else:
            state_features = torch.zeros_like(visual_features)
        fused = self.fusion(torch.cat([visual_features, state_features], dim=-1))
        fused = fused + self.position_embedding[:, :seq_len]
        if causal and seq_len > 1:
            mask = torch.triu(
                torch.ones(seq_len, seq_len, device=frames.device, dtype=torch.bool),
                diagonal=1
            )
        else:
            mask = None
        hidden = self.transformer(fused, mask=mask)
        gate = self.memory_gate(torch.cat([hidden, fused], dim=-1))
        hidden = hidden + gate * fused
        return {
            "button_logits": self.button_head(hidden),
            "continuous_actions": self.continuous_head(hidden),
            "state_values": self.value_head(hidden),
            "reward_predictions": self.reward_head(hidden),
            "done_logits": self.done_head(hidden),
            "next_latent": self.world_model(hidden),
            "hidden_states": hidden
        }

    @torch.no_grad()
    def act(self, frames, state=None, threshold=0.5):
        self.eval()
        outputs = self.forward(frames, state, causal=True)
        button_probabilities = torch.sigmoid(outputs["button_logits"][:, -1])
        return {
            "buttons": (button_probabilities >= threshold).int(),
            "button_probabilities": button_probabilities,
            "continuous": outputs["continuous_actions"][:, -1],
            "value": outputs["state_values"][:, -1],
            "predicted_reward": outputs["reward_predictions"][:, -1],
            "predicted_done": torch.sigmoid(outputs["done_logits"][:, -1])
        }


def create_uga(device=None):
    model = UniversalGameNet(
        state_dim=128,
        num_buttons=32,
        continuous_dim=4,
        d_model=512,
        num_layers=12,
        num_heads=8,
        max_seq_len=128,
        dropout=0.1
    )
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    return model.to(device)


if __name__ == "__main__":
    model = create_uga()
    frames = torch.rand(2, 8, 3, 224, 224)
    state = torch.rand(2, 8, 128)
    outputs = model(frames, state)
    for name, tensor in outputs.items():
        print(name, tuple(tensor.shape))
    print("Parameters:", sum(p.numel() for p in model.parameters()))
