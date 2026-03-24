"""
Deepfake Detection — uses HuggingFace transformers with
dima806/deepfake_vs_real_image_detection model loaded locally.

Runs inference on-device. No API key required.
"""

import asyncio
import io
import logging
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)

# Lazy-loaded globals — model downloads once on first call
_processor = None
_model = None
_load_failed = False


def _load_model():
    """Load the model and processor on first use (downloads ~350MB once)."""
    global _processor, _model, _load_failed

    if _load_failed:
        return False
    if _processor is not None and _model is not None:
        return True

    try:
        from transformers import AutoImageProcessor, AutoModelForImageClassification

        logger.info("Loading deepfake detection model (first run downloads ~350MB)...")
        _processor = AutoImageProcessor.from_pretrained(
            "dima806/deepfake_vs_real_image_detection"
        )
        _model = AutoModelForImageClassification.from_pretrained(
            "dima806/deepfake_vs_real_image_detection"
        )
        logger.info("Deepfake detection model loaded successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to load deepfake model: {e}")
        _load_failed = True
        return False


def _run_inference(image: Image.Image) -> dict:
    """Run inference synchronously (meant to be called via asyncio.to_thread)."""
    import torch

    if not _load_model():
        return {
            "deepfake_probability": 0,
            "confidence": 0,
            "label": "Unavailable",
            "summary": "Deepfake model failed to load. Check logs for details.",
            "model": "dima806/deepfake_vs_real_image_detection",
        }

    inputs = _processor(images=image, return_tensors="pt")

    with torch.no_grad():
        outputs = _model(**inputs)

    logits = outputs.logits
    probs = torch.nn.functional.softmax(logits, dim=-1)[0]

    # Map model labels to scores
    id2label = _model.config.id2label
    results = {}
    for idx, prob in enumerate(probs):
        label = id2label.get(idx, f"class_{idx}").lower()
        results[label] = float(prob)

    # Extract fake/real scores
    fake_score = 0.0
    real_score = 0.0
    for label, score in results.items():
        if "fake" in label or "deepfake" in label:
            fake_score = score
        elif "real" in label:
            real_score = score

    deepfake_probability = round(fake_score * 100, 1)
    confidence = round(max(fake_score, real_score) * 100, 1)

    if deepfake_probability > 70:
        verdict_label = "Deepfake"
        summary = (
            f"This image is highly likely to be a deepfake ({deepfake_probability}% probability). "
            f"The deep learning model identifies strong facial manipulation signals."
        )
    elif deepfake_probability > 40:
        verdict_label = "Suspicious"
        summary = (
            f"This image shows mixed signals ({deepfake_probability}% deepfake probability). "
            f"Some characteristics suggest manipulation while others appear authentic."
        )
    else:
        verdict_label = "Real"
        summary = (
            f"This image appears to be authentic ({deepfake_probability}% deepfake probability). "
            f"The model finds it consistent with a real photograph."
        )

    return {
        "deepfake_probability": deepfake_probability,
        "confidence": confidence,
        "label": verdict_label,
        "summary": summary,
        "model": "dima806/deepfake_vs_real_image_detection",
    }


async def detect_deepfake(image_data: bytes, filename: str = "") -> dict:
    """
    Analyze an image for deepfake signals using a local HuggingFace model.
    Runs on CPU. No API key required.
    """
    try:
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
    except Exception as e:
        logger.error(f"Cannot open image for deepfake detection: {e}")
        return {
            "deepfake_probability": 0,
            "confidence": 0,
            "label": "Error",
            "summary": f"Cannot decode image: {str(e)}",
            "model": "dima806/deepfake_vs_real_image_detection",
        }

    try:
        result = await asyncio.to_thread(_run_inference, image)
        return result
    except Exception as e:
        logger.error(f"Deepfake detection failed: {e}")
        return {
            "deepfake_probability": 0,
            "confidence": 0,
            "label": "Error",
            "summary": f"Deepfake detection failed: {str(e)}",
            "model": "dima806/deepfake_vs_real_image_detection",
        }
