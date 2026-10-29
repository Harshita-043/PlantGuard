"""
Native PyTorch DINOv2 Architecture.

Implements the official Meta DINOv2 Vision Transformer architecture for:
1. DINOv2 Small (dinov2_vits14): embed_dim=384, depth=12, num_heads=6
2. DINOv2 Base (dinov2_vitb14): embed_dim=768, depth=12, num_heads=12

Enables strict-mode loading of local weights without external network calls
or dependencies on torch.hub / Hugging Face Hub downloads.
"""

import math
from typing import Any, Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


class LayerScale(nn.Module):
    """LayerScale residual scaling parameter."""

    def __init__(self, dim: int, init_values: float = 1e-5):
        super().__init__()
        self.gamma = nn.Parameter(init_values * torch.ones(dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x * self.gamma


class Attention(nn.Module):
    """Multi-Head Self-Attention with QKV projection."""

    def __init__(self, dim: int, num_heads: int = 6):
        super().__init__()
        self.num_heads = num_heads
        self.head_dim = dim // num_heads
        self.scale = self.head_dim ** -0.5
        self.qkv = nn.Linear(dim, dim * 3, bias=True)
        self.proj = nn.Linear(dim, dim, bias=True)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        B, N, C = x.shape
        qkv = self.qkv(x).reshape(B, N, 3, self.num_heads, self.head_dim).permute(2, 0, 3, 1, 4)
        q, k, v = qkv[0], qkv[1], qkv[2]

        attn = (q @ k.transpose(-2, -1)) * self.scale
        attn = attn.softmax(dim=-1)

        out = (attn @ v).transpose(1, 2).reshape(B, N, C)
        out = self.proj(out)
        return out, attn


class MLP(nn.Module):
    """Feed-Forward Network with GELU activation."""

    def __init__(self, in_features: int, hidden_features: int):
        super().__init__()
        self.fc1 = nn.Linear(in_features, hidden_features, bias=True)
        self.act = nn.GELU()
        self.fc2 = nn.Linear(hidden_features, in_features, bias=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.fc2(self.act(self.fc1(x)))


class Block(nn.Module):
    """DINOv2 Transformer Encoder Block with LayerScale."""

    def __init__(self, dim: int, num_heads: int, mlp_ratio: float = 4.0):
        super().__init__()
        self.norm1 = nn.LayerNorm(dim, eps=1e-6)
        self.attn = Attention(dim, num_heads=num_heads)
        self.ls1 = LayerScale(dim)
        self.norm2 = nn.LayerNorm(dim, eps=1e-6)
        self.mlp = MLP(dim, int(dim * mlp_ratio))
        self.ls2 = LayerScale(dim)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        attn_out, attn_map = self.attn(self.norm1(x))
        x = x + self.ls1(attn_out)
        x = x + self.ls2(self.mlp(self.norm2(x)))
        return x, attn_map


class PatchEmbed(nn.Module):
    """Image to Patch Embedding via 2D Convolution."""

    def __init__(self, patch_size: int = 14, in_chans: int = 3, embed_dim: int = 384):
        super().__init__()
        self.patch_size = patch_size
        self.proj = nn.Conv2d(in_chans, embed_dim, kernel_size=patch_size, stride=patch_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.proj(x)
        x = x.flatten(2).transpose(1, 2)
        return x


class DinoBackbone(nn.Module):
    """
    DINOv2 Vision Transformer Backbone.
    Positional embeddings interpolate smoothly between 518x518 training resolution
    and 224x224 inference resolution.
    """

    def __init__(
        self,
        patch_size: int = 14,
        embed_dim: int = 384,
        depth: int = 12,
        num_heads: int = 6,
    ):
        super().__init__()
        self.patch_size = patch_size
        self.embed_dim = embed_dim
        self.cls_token = nn.Parameter(torch.zeros(1, 1, embed_dim))
        self.pos_embed = nn.Parameter(torch.zeros(1, 1370, embed_dim))
        self.mask_token = nn.Parameter(torch.zeros(1, embed_dim))
        self.patch_embed = PatchEmbed(patch_size, in_chans=3, embed_dim=embed_dim)
        self.blocks = nn.ModuleList([Block(embed_dim, num_heads) for _ in range(depth)])
        self.norm = nn.LayerNorm(embed_dim, eps=1e-6)

    def interpolate_pos_encoding(self, x: torch.Tensor, w: int, h: int) -> torch.Tensor:
        """Bicubic positional embedding interpolation."""
        npatch = x.shape[1] - 1
        N = self.pos_embed.shape[1] - 1
        if npatch == N and w == h:
            return self.pos_embed

        class_pos_embed = self.pos_embed[:, 0]
        patch_pos_embed = self.pos_embed[:, 1:]
        dim = x.shape[-1]
        w0 = w // self.patch_size
        h0 = h // self.patch_size
        w0, h0 = w0 + 0.1, h0 + 0.1
        M = int(math.sqrt(N))

        patch_pos_embed = patch_pos_embed.reshape(1, M, M, dim).permute(0, 3, 1, 2)
        patch_pos_embed = F.interpolate(
            patch_pos_embed,
            scale_factor=(w0 / M, h0 / M),
            mode="bicubic",
            align_corners=False,
            antialias=True,
        )
        patch_pos_embed = patch_pos_embed.permute(0, 2, 3, 1).view(1, -1, dim)
        return torch.cat((class_pos_embed.unsqueeze(0), patch_pos_embed), dim=1)

    def forward(
        self,
        x: torch.Tensor,
        return_attention: bool = False,
        return_all_attentions: bool = False,
    ) -> Tuple[torch.Tensor, Any]:
        B, C, H, W = x.shape
        tokens = self.patch_embed(x)
        cls_tokens = self.cls_token.expand(B, -1, -1)
        tokens = torch.cat((cls_tokens, tokens), dim=1)

        pos = self.interpolate_pos_encoding(tokens, W, H)
        tokens = tokens + pos

        all_attns = []
        last_attn = None
        for blk in self.blocks:
            tokens, last_attn = blk(tokens)
            if return_all_attentions:
                all_attns.append(last_attn)

        tokens = self.norm(tokens)
        cls_output = tokens[:, 0]

        if return_all_attentions:
            return cls_output, all_attns
        if return_attention:
            return cls_output, last_attn
        return cls_output, None


class DinoClassifierModel(nn.Module):
    """
    Complete classifier with DINOv2 backbone and linear projection head.
    Matches exact state_dict structure:
      - backbone.*
      - head.0 (LayerNorm)
      - head.1 (Linear)
    """

    def __init__(
        self,
        embed_dim: int = 384,
        num_classes: int = 1,
        depth: int = 12,
        num_heads: int = 6,
    ):
        super().__init__()
        self.backbone = DinoBackbone(
            patch_size=14,
            embed_dim=embed_dim,
            depth=depth,
            num_heads=num_heads,
        )
        self.head = nn.Sequential(
            nn.LayerNorm(embed_dim),
            nn.Linear(embed_dim, num_classes),
        )

    def forward(
        self,
        x: torch.Tensor,
        return_attention: bool = False,
        return_all_attentions: bool = False,
    ):
        feat, attn = self.backbone(
            x,
            return_attention=return_attention,
            return_all_attentions=return_all_attentions,
        )
        logits = self.head(feat)
        if return_attention or return_all_attentions:
            return logits, attn
        return logits


def build_dino_leaf_filter() -> DinoClassifierModel:
    """Build DINOv2 Small model for binary leaf filtering."""
    return DinoClassifierModel(embed_dim=384, num_classes=1, depth=12, num_heads=6)


def build_dino_disease_classifier() -> DinoClassifierModel:
    """Build DINOv2 Base model for 38-class disease classification."""
    return DinoClassifierModel(embed_dim=768, num_classes=38, depth=12, num_heads=12)
