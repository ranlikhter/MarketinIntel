"""
Image-Based Product Matcher
Uses OpenCLIP (ViT-B/32) to generate 512-dim visual embeddings and compute
cosine similarity between product images.  Used as a second-pass tiebreaker
when text-only match scores fall in the ambiguous 0.70–0.85 range.

Model is lazy-loaded on first use (~1-2 s) and reused across calls.
All network / model errors are caught; functions return None so the caller
can fall back to text-only scoring without crashing.
"""

from __future__ import annotations

import io
import logging
import threading
from typing import Optional

import httpx
import numpy as np

logger = logging.getLogger(__name__)

# ── Model singleton ────────────────────────────────────────────────────────────

_model = None
_preprocess = None
_model_lock = threading.Lock()
_MODEL_NAME = "ViT-B-32"
_PRETRAINED = "openai"


def _load_model():
    """Lazy-load OpenCLIP model — safe to call from multiple threads."""
    global _model, _preprocess
    if _model is not None:
        return _model, _preprocess
    with _model_lock:
        if _model is not None:
            return _model, _preprocess
        try:
            import open_clip
            import torch
            m, _, pre = open_clip.create_model_and_transforms(
                _MODEL_NAME, pretrained=_PRETRAINED
            )
            m.eval()
            _model = m
            _preprocess = pre
            logger.info("OpenCLIP model loaded (%s / %s)", _MODEL_NAME, _PRETRAINED)
        except Exception as exc:
            logger.warning("Could not load OpenCLIP model: %s", exc)
            _model = None
            _preprocess = None
    return _model, _preprocess


# ── Core functions ─────────────────────────────────────────────────────────────

def embed_image_url(url: str, timeout: float = 6.0) -> Optional[list]:
    """
    Fetch image at *url* and return a normalised 512-dim CLIP embedding
    as a plain Python list[float], or None if the image cannot be fetched
    or embedded (network error, 4xx/5xx, unsupported format, model failure).
    """
    if not url or not url.startswith(("http://", "https://")):
        return None

    try:
        resp = httpx.get(
            url, timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (compatible; MarketIntel/1.0)"},
            follow_redirects=True,
        )
        resp.raise_for_status()
        raw = resp.content
    except Exception as exc:
        logger.debug("Image fetch failed for %s: %s", url, exc)
        return None

    try:
        from PIL import Image
        img = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as exc:
        logger.debug("Image decode failed for %s: %s", url, exc)
        return None

    model, preprocess = _load_model()
    if model is None or preprocess is None:
        return None

    try:
        import torch
        tensor = preprocess(img).unsqueeze(0)
        with torch.no_grad():
            emb = model.encode_image(tensor)
            emb = emb / emb.norm(dim=-1, keepdim=True)
        return emb[0].tolist()
    except Exception as exc:
        logger.debug("Embedding failed for %s: %s", url, exc)
        return None


def cosine_similarity(a: list, b: list) -> float:
    """
    Cosine similarity between two embedding vectors.
    Both are assumed to be unit-normalised (output of embed_image_url).
    Returns 0.0 if either vector is missing or lengths differ.
    """
    if not a or not b or len(a) != len(b):
        return 0.0
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    dot = float(np.dot(va, vb))
    # Clamp to [-1, 1] to guard against floating-point drift
    return max(-1.0, min(1.0, dot))


def compare_urls(url1: str, url2: str) -> Optional[float]:
    """
    Fetch both image URLs, embed them, and return cosine similarity [0, 1].
    Returns None if either image cannot be embedded (caller falls back to text).
    """
    emb1 = embed_image_url(url1)
    if emb1 is None:
        return None
    emb2 = embed_image_url(url2)
    if emb2 is None:
        return None
    sim = cosine_similarity(emb1, emb2)
    # CLIP cosine similarities typically range 0.5–1.0 for related images;
    # rescale to 0–1 so it's directly comparable with text match scores.
    return (sim + 1.0) / 2.0


def compare_embeddings(emb1: list, emb2: list) -> float:
    """
    Compare two pre-computed embeddings (e.g. stored in DB).
    Rescales cosine similarity from [-1,1] to [0,1].
    """
    raw = cosine_similarity(emb1, emb2)
    return (raw + 1.0) / 2.0
