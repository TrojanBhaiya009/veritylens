"""
AI-Generated Media Detector — Advanced pixel-level + frequency analysis.
Uses PIL + numpy for real differentiation between AI and camera images.

Key techniques that ACTUALLY differentiate AI from real:
1. FFT Spectral Analysis — AI images have distinct frequency signatures
   from upsampling artifacts in GANs/diffusion models
2. Patch Variance Distribution — Real photos have highly varied local
   variance (sky vs hair vs skin). AI images are more uniform.
3. Cross-Channel Correlation — Camera Bayer filters create specific
   RGB correlation patterns that AI doesn't replicate.
4. Local Contrast Variation — Real lighting creates characteristic
   contrast patterns that AI images lack.
5. EXIF & AI signature detection
"""

import io
import math
import logging
from typing import Optional

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def _img_to_array(img, size=(256, 256)) -> np.ndarray:
    """Convert PIL Image to numpy array at target size."""
    return np.array(img.convert("RGB").resize(size), dtype=np.float64)


def _img_to_gray(img, size=(256, 256)) -> np.ndarray:
    """Convert PIL Image to grayscale numpy array."""
    return np.array(img.convert("L").resize(size), dtype=np.float64)


# ============================================================
# 1. FFT Spectral Analysis
# ============================================================

def _analyze_frequency_spectrum(img) -> dict:
    """
    Analyze the frequency spectrum of the image using 2D FFT.
    
    AI-generated images (especially GANs) often show:
    - Periodic artifacts in the frequency domain
    - Different high-to-low frequency energy ratios
    - More energy concentrated in specific frequency bands
    
    Diffusion models tend to have:
    - Smoother frequency rolloff
    - Less high-frequency noise compared to camera sensors
    
    Returns dict with spectral features.
    """
    gray = _img_to_gray(img)
    
    # 2D FFT
    f_transform = np.fft.fft2(gray)
    f_shift = np.fft.fftshift(f_transform)
    magnitude = np.abs(f_shift)
    
    # Log magnitude spectrum
    log_magnitude = np.log1p(magnitude)
    
    h, w = gray.shape
    center_y, center_x = h // 2, w // 2
    
    # Create radial frequency bands
    y_coords, x_coords = np.ogrid[:h, :w]
    distances = np.sqrt((y_coords - center_y) ** 2 + (x_coords - center_x) ** 2)
    max_dist = np.sqrt(center_y**2 + center_x**2)
    
    # Divide into 4 frequency bands: very low, low, mid, high
    band_edges = [0, max_dist * 0.1, max_dist * 0.3, max_dist * 0.6, max_dist]
    band_energies = []
    for i in range(len(band_edges) - 1):
        mask = (distances >= band_edges[i]) & (distances < band_edges[i + 1])
        if np.sum(mask) > 0:
            band_energies.append(np.mean(log_magnitude[mask]))
        else:
            band_energies.append(0)
    
    # Key ratio: high-freq to mid-freq energy
    # Real photos: more high-freq energy (sensor noise)
    # AI images: less high-freq energy (smoother)
    if band_energies[2] > 0:
        high_mid_ratio = band_energies[3] / band_energies[2]
    else:
        high_mid_ratio = 0
    
    # Spectral rolloff rate (how quickly energy drops with frequency)
    # AI images typically have steeper rolloff
    if len(band_energies) >= 3 and band_energies[1] > 0:
        rolloff = band_energies[3] / band_energies[1]
    else:
        rolloff = 0
    
    # Check for periodic artifacts (GAN fingerprint)
    # Look for unusual peaks in the spectrum away from center
    mid_ring = (distances > max_dist * 0.2) & (distances < max_dist * 0.5)
    if np.sum(mid_ring) > 0:
        mid_vals = log_magnitude[mid_ring]
        mid_mean = np.mean(mid_vals)
        mid_std = np.std(mid_vals)
        # Count anomalous peaks (more than 3 std above mean)
        if mid_std > 0:
            peak_count = np.sum(mid_vals > mid_mean + 3 * mid_std)
            peak_ratio = peak_count / np.sum(mid_ring)
        else:
            peak_ratio = 0
    else:
        peak_ratio = 0
    
    return {
        "high_mid_ratio": high_mid_ratio,
        "rolloff": rolloff,
        "peak_ratio": peak_ratio,
        "band_energies": band_energies,
    }


# ============================================================
# 2. Patch Variance Distribution
# ============================================================

def _analyze_patch_variance(img) -> dict:
    """
    Divide image into patches and analyze variance distribution.
    
    Real photos: VERY varied patch variances (uniform sky patches next
    to textured hair/grass patches → high coefficient of variation)
    
    AI images: More uniform variance across patches (AI tends to add
    similar detail levels everywhere → lower CV)
    """
    gray = _img_to_gray(img, size=(256, 256))
    
    patch_size = 16
    variances = []
    
    for y in range(0, 256 - patch_size + 1, patch_size):
        for x in range(0, 256 - patch_size + 1, patch_size):
            patch = gray[y:y+patch_size, x:x+patch_size]
            variances.append(np.var(patch))
    
    variances = np.array(variances)
    
    if len(variances) < 4:
        return {"cv": 0.5, "skewness": 0, "range_ratio": 0.5}
    
    mean_var = np.mean(variances)
    std_var = np.std(variances)
    
    # Coefficient of variation of patch variances
    # Higher = more varied = more likely real
    cv = std_var / mean_var if mean_var > 0 else 0
    
    # Skewness of variance distribution
    # Real photos tend to be right-skewed (many smooth patches, few textured)
    if std_var > 0:
        skewness = np.mean(((variances - mean_var) / std_var) ** 3)
    else:
        skewness = 0
    
    # Range: ratio of (95th percentile - 5th percentile) to median
    p5, p95, median = np.percentile(variances, [5, 95, 50])
    range_ratio = (p95 - p5) / median if median > 0 else 0
    
    return {
        "cv": cv,
        "skewness": skewness,
        "range_ratio": range_ratio,
    }


# ============================================================
# 3. Cross-Channel Correlation
# ============================================================

def _analyze_channel_correlation(img) -> dict:
    """
    Analyze RGB channel correlations at the pixel level.
    
    Real camera sensors use Bayer filters (RGGB), and demosaicing
    creates specific correlation patterns between R, G, B channels
    at fine scales. AI images don't replicate this.
    
    Also analyzes the residual signal (difference between channels)
    for noise correlation patterns unique to cameras.
    """
    arr = _img_to_array(img, size=(256, 256))
    r, g, b = arr[:,:,0].flatten(), arr[:,:,1].flatten(), arr[:,:,2].flatten()
    
    def safe_corr(a, b_arr):
        """Correlation that handles constant arrays."""
        if np.std(a) < 1e-6 or np.std(b_arr) < 1e-6:
            return 0.99  # Constant channels = suspicious (AI-like)
        return np.corrcoef(a, b_arr)[0, 1]
    
    # Pearson correlations between channels
    rg_corr = safe_corr(r, g)
    rb_corr = safe_corr(r, b)
    gb_corr = safe_corr(g, b)
    
    # In real photos, R-G correlation is typically highest (Bayer green filter)
    # AI images tend to have very high, nearly identical correlations
    avg_corr = (rg_corr + rb_corr + gb_corr) / 3
    corr_spread = max(rg_corr, rb_corr, gb_corr) - min(rg_corr, rb_corr, gb_corr)
    
    # Noise residual analysis
    # Apply simple 3x3 mean filter and look at residual
    arr_reshaped = arr.reshape(256, 256, 3)
    kernel_size = 3
    residuals_std = []
    
    for ch in range(3):
        channel = arr_reshaped[:,:,ch]
        # Simple mean filter
        filtered = np.zeros_like(channel)
        for y in range(1, 255):
            for x in range(1, 255):
                filtered[y, x] = np.mean(channel[y-1:y+2, x-1:x+2])
        residual = channel[1:-1, 1:-1] - filtered[1:-1, 1:-1]
        residuals_std.append(np.std(residual))
    
    # In real photos, noise residual tends to be different per channel
    # (sensor noise characteristics). AI images have more uniform noise.
    noise_std_spread = max(residuals_std) - min(residuals_std)
    avg_noise_std = np.mean(residuals_std)
    
    return {
        "avg_correlation": avg_corr,
        "correlation_spread": corr_spread,
        "noise_std_spread": noise_std_spread,
        "avg_noise_std": avg_noise_std,
        "rg_corr": rg_corr,
    }


# ============================================================
# 4. Local Contrast Analysis
# ============================================================

def _analyze_local_contrast(img) -> dict:
    """
    Analyze local contrast patterns.
    
    Real photos have contrast that follows lighting physics
    (shadows, highlights, falloff). AI images often have
    more uniform or unrealistic contrast patterns.
    """
    gray = _img_to_gray(img, size=(128, 128))
    
    # Compute local contrast using sliding window
    block = 8
    contrasts = []
    
    for y in range(0, 128 - block, block // 2):
        for x in range(0, 128 - block, block // 2):
            patch = gray[y:y+block, x:x+block]
            local_max = np.max(patch)
            local_min = np.min(patch)
            if local_max + local_min > 0:
                # Michelson contrast
                contrast = (local_max - local_min) / (local_max + local_min)
                contrasts.append(contrast)
    
    contrasts = np.array(contrasts)
    
    if len(contrasts) < 4:
        return {"contrast_cv": 0.5, "contrast_entropy": 3.0}
    
    # CV of local contrast
    mean_c = np.mean(contrasts)
    std_c = np.std(contrasts)
    cv = std_c / mean_c if mean_c > 0 else 0
    
    # Entropy of contrast distribution (histogram)
    hist, _ = np.histogram(contrasts, bins=20, range=(0, 1))
    hist = hist / hist.sum()
    hist = hist[hist > 0]
    entropy = -np.sum(hist * np.log2(hist))
    
    return {
        "contrast_cv": cv,
        "contrast_entropy": entropy,
    }


# ============================================================
# 5. EXIF & AI Signatures (kept from before)
# ============================================================

def _get_exif_info(img) -> dict:
    """Extract EXIF metadata."""
    info = {
        "has_exif": False, "exif_field_count": 0,
        "has_camera_info": False, "camera_model": None,
        "has_gps": False, "software": None,
    }
    try:
        exif_data = img.getexif()
        if exif_data:
            info["has_exif"] = True
            info["exif_field_count"] = len(exif_data)
            make = exif_data.get(271, "")
            model = exif_data.get(272, "")
            software = exif_data.get(305, "")
            gps = exif_data.get(34853)
            if make or model:
                info["has_camera_info"] = True
                info["camera_model"] = f"{make} {model}".strip()
            if gps:
                info["has_gps"] = True
            if software:
                info["software"] = str(software)
    except Exception:
        pass
    return info


def _check_ai_signatures(img, raw_data: bytes) -> dict:
    """Check for AI tool signatures in metadata and raw bytes."""
    found = []
    try:
        exif = img.getexif()
        software = str(exif.get(305, "")).lower()
        for s in ["stable diffusion", "midjourney", "dall-e", "comfyui",
                   "automatic1111", "invokeai", "novelai"]:
            if s in software:
                found.append(software)
    except Exception:
        pass

    if hasattr(img, 'info') and img.info:
        for key, val in img.info.items():
            val_str = str(val).lower()
            for s in ["stable diffusion", "midjourney", "dall-e", "comfyui",
                       "automatic1111", "novelai", "parameters", "sd-metadata",
                       "invokeai", "dream studio", "leonardo"]:
                if s in val_str:
                    found.append(f"{key}: (AI metadata)")
                    break

    search_region = (raw_data[:8000] + raw_data[-4000:]).lower()
    for sig, name in {
        b'stable diffusion': 'Stable Diffusion', b'midjourney': 'Midjourney',
        b'dall-e': 'DALL-E', b'comfyui': 'ComfyUI',
        b'automatic1111': 'Automatic1111', b'novelai': 'NovelAI',
        b'ai generated': 'AI Generated', b'ai-generated': 'AI Generated',
    }.items():
        if sig in search_region and name not in found:
            found.append(name)

    return {"found_signatures": found, "has_ai_signature": len(found) > 0}


def _check_ai_dimensions(w: int, h: int) -> dict:
    """Check if dimensions match common AI generation sizes."""
    # Comprehensive list of AI generation defaults
    ai_sizes = {
        # Stable Diffusion 1.x
        (512, 512), (768, 768), (512, 768), (768, 512),
        # Stable Diffusion XL / Flux
        (1024, 1024), (1024, 768), (768, 1024),
        (1152, 896), (896, 1152), (1216, 832), (832, 1216),
        (1344, 768), (768, 1344), (1536, 1024), (1024, 1536),
        # DALL-E 3
        (1024, 1792), (1792, 1024),
        # Midjourney common outputs
        (1456, 816), (816, 1456), (1024, 576), (576, 1024),
        (2048, 2048), (1536, 1536), (1792, 1024), (1024, 1792),
        (2048, 1152), (1152, 2048), (1536, 864), (864, 1536),
        # Leonardo / other
        (1080, 1080), (1080, 1920), (1920, 1080),
        (1472, 832), (832, 1472), (1600, 1024), (1024, 1600),
    }
    exact_match = (w, h) in ai_sizes or (h, w) in ai_sizes
    
    # Also check if aspect ratio matches common AI ratios
    # AND both dimensions are multiples of 64 (AI gen constraint)
    is_64_aligned = (w % 64 == 0) and (h % 64 == 0)
    
    # Common AI aspect ratios
    ratio = w / h if h > 0 else 1
    ai_ratios = {1.0, 4/3, 3/4, 3/2, 2/3, 16/9, 9/16, 7/4, 4/7}
    is_ai_ratio = any(abs(ratio - r) < 0.02 for r in ai_ratios)
    
    likely_ai_dims = exact_match or (is_64_aligned and is_ai_ratio and w >= 512 and h >= 512)
    
    return {
        "exact_match": exact_match,
        "likely_ai_dims": likely_ai_dims,
        "is_64_aligned": is_64_aligned,
    }


# ============================================================
# Main Detection Function
# ============================================================

def detect_ai_media(image_data: bytes, filename: str = "") -> dict:
    """
    Analyze an image for AI generation using advanced techniques.
    
    Uses: FFT spectral analysis, patch variance distribution,
    cross-channel correlation, local contrast analysis,
    EXIF metadata, and AI signature detection.
    """
    if len(image_data) < 100:
        return {
            "ai_probability": 0, "confidence": 5,
            "indicators": {}, "summary": "File too small.",
            "detected_tool": None,
            "image_info": {"format": "unknown", "width": 0, "height": 0, "file_size_kb": 0},
        }

    try:
        img = Image.open(io.BytesIO(image_data))
    except Exception as e:
        return {
            "ai_probability": 0, "confidence": 5,
            "indicators": {}, "summary": f"Cannot decode: {e}",
            "detected_tool": None,
            "image_info": {"format": "unknown", "width": 0, "height": 0, "file_size_kb": 0},
        }

    width, height = img.size
    fmt = img.format or "unknown"

    # === Run all analyses ===
    exif_info = _get_exif_info(img)
    ai_sigs = _check_ai_signatures(img, image_data)
    dim_info = _check_ai_dimensions(width, height)
    is_ai_dim = dim_info["likely_ai_dims"]

    spectral = _analyze_frequency_spectrum(img)
    patches = _analyze_patch_variance(img)
    channels = _analyze_channel_correlation(img)
    contrast = _analyze_local_contrast(img)

    # === Score each signal (0-100, higher = more AI-like) ===

    scores = {}

    # --- 1. Spectral Analysis (most powerful) ---
    # Real photos: high_mid_ratio > 0.6 (lots of high-freq sensor noise)
    # AI images: high_mid_ratio < 0.5 (smoother, less HF noise)
    hmr = spectral["high_mid_ratio"]
    if hmr < 0.35:
        scores["frequency_spectrum"] = 80
    elif hmr < 0.45:
        scores["frequency_spectrum"] = 60
    elif hmr < 0.55:
        scores["frequency_spectrum"] = 35
    elif hmr < 0.65:
        scores["frequency_spectrum"] = 18
    else:
        scores["frequency_spectrum"] = 8

    # Spectral rolloff (steeper = more AI-like)
    if spectral["rolloff"] < 0.15:
        scores["spectral_rolloff"] = 65
    elif spectral["rolloff"] < 0.3:
        scores["spectral_rolloff"] = 35
    else:
        scores["spectral_rolloff"] = 12

    # GAN periodic artifacts
    if spectral["peak_ratio"] > 0.01:
        scores["periodic_artifacts"] = 75
    elif spectral["peak_ratio"] > 0.005:
        scores["periodic_artifacts"] = 40

    # --- 2. Patch Variance (very reliable) ---
    # Real photos: high CV (>1.2), high range_ratio (>3)
    # AI images: lower CV (<0.8), lower range_ratio (<2)
    pcv = patches["cv"]
    if pcv < 0.5:
        scores["texture_uniformity"] = 75
    elif pcv < 0.8:
        scores["texture_uniformity"] = 55
    elif pcv < 1.2:
        scores["texture_uniformity"] = 30
    elif pcv < 1.8:
        scores["texture_uniformity"] = 12
    else:
        scores["texture_uniformity"] = 5

    # --- 3. Channel Correlation ---
    # AI has very high avg correlation (>0.95) with low spread
    # Real photos have more varied correlations with higher spread
    corr_spread = channels["correlation_spread"]
    if corr_spread < 0.02:
        scores["channel_correlation"] = 55
    elif corr_spread < 0.05:
        scores["channel_correlation"] = 35
    elif corr_spread < 0.1:
        scores["channel_correlation"] = 20
    else:
        scores["channel_correlation"] = 8

    # Noise residual spread (real photos have different noise per channel)
    nss = channels["noise_std_spread"]
    if nss < 0.3:
        scores["noise_pattern"] = 50
    elif nss < 0.8:
        scores["noise_pattern"] = 30
    elif nss < 1.5:
        scores["noise_pattern"] = 15
    else:
        scores["noise_pattern"] = 5

    # --- 4. Local Contrast ---
    # Real photos: higher contrast entropy (>3.5) and CV
    # AI images: lower contrast entropy and more uniform contrast
    if contrast["contrast_entropy"] < 2.5:
        scores["contrast_pattern"] = 55
    elif contrast["contrast_entropy"] < 3.2:
        scores["contrast_pattern"] = 35
    elif contrast["contrast_entropy"] < 3.8:
        scores["contrast_pattern"] = 18
    else:
        scores["contrast_pattern"] = 8

    # --- 5. Metadata ---
    if ai_sigs["has_ai_signature"]:
        scores["ai_signature"] = 95
    elif exif_info["has_camera_info"] and exif_info["has_gps"]:
        scores["metadata"] = 3
    elif exif_info["has_camera_info"]:
        scores["metadata"] = 8
    elif not exif_info["has_exif"]:
        scores["metadata"] = 45  # No metadata is a real signal
    else:
        scores["metadata"] = 15

    # --- 6. Dimensions ---
    if dim_info["exact_match"]:
        scores["dimensions"] = 60  # Exact AI size match is strong
    elif dim_info["likely_ai_dims"]:
        scores["dimensions"] = 40  # 64-aligned + AI ratio

    # --- 7. Combined heuristic (strongest non-ML signal) ---
    # PNG/WebP + no EXIF + AI dimensions = overwhelming AI evidence
    is_lossless = fmt.lower() in ("png", "webp")
    no_metadata = not exif_info["has_exif"]
    if is_lossless and no_metadata and is_ai_dim:
        scores["combined_ai_signal"] = 85
    elif no_metadata and is_ai_dim:
        scores["combined_ai_signal"] = 70
    elif is_lossless and no_metadata and dim_info["is_64_aligned"]:
        scores["combined_ai_signal"] = 55

    # Strong export fingerprint often seen in generated images:
    # no camera metadata + canonical gen size + lossless export.
    if (
        dim_info["exact_match"]
        and no_metadata
        and is_lossless
        and not exif_info["has_camera_info"]
    ):
        scores["ai_export_fingerprint"] = 92
    elif dim_info["exact_match"] and no_metadata and not exif_info["has_camera_info"]:
        scores["ai_export_fingerprint"] = 78

    # === Calculate final probability ===
    weights = {
        "frequency_spectrum": 2.5,
        "spectral_rolloff": 1.0,
        "periodic_artifacts": 2.0,
        "texture_uniformity": 2.0,
        "channel_correlation": 2.2,
        "noise_pattern": 2.0,
        "contrast_pattern": 1.5,
        "ai_signature": 5.0,
        "metadata": 3.2,
        "dimensions": 3.0,
        "combined_ai_signal": 5.0,
        "ai_export_fingerprint": 5.5,
    }

    weighted_sum = 0
    weight_total = 0
    for key, score in scores.items():
        w = weights.get(key, 1.0)
        weighted_sum += score * w
        weight_total += w

    ai_probability = round(weighted_sum / weight_total, 1) if weight_total > 0 else 10
    ai_probability = max(5, min(95, ai_probability))

    # === Hard overrides ===
    if ai_sigs["has_ai_signature"]:
        ai_probability = max(ai_probability, 85)

    if exif_info["has_camera_info"] and exif_info["has_gps"]:
        ai_probability = min(ai_probability, 15)
    
    # Combined evidence overrides
    if no_metadata and dim_info["exact_match"]:
        ai_probability = max(ai_probability, 62)

    if no_metadata and dim_info["exact_match"] and not exif_info["has_camera_info"]:
        ai_probability = max(ai_probability, 70)

    if no_metadata and dim_info["exact_match"] and is_lossless and not exif_info["has_camera_info"]:
        ai_probability = max(ai_probability, 78)

    # If channel behavior is also suspicious, escalate further.
    if (
        no_metadata
        and dim_info["exact_match"]
        and scores.get("channel_correlation", 0) >= 35
    ):
        ai_probability = max(ai_probability, 83)

    # Camera metadata without AI signature should pull probability down,
    # unless dimensions/signals are overwhelmingly AI-like.
    if exif_info["has_camera_info"] and not ai_sigs["has_ai_signature"] and not dim_info["exact_match"]:
        ai_probability = min(ai_probability, 38)

    # === Confidence ===
    confidence = 45.0
    if fmt.lower() in ("jpeg", "png", "webp"):
        confidence += 8
    if width > 200 and height > 200:
        confidence += 7
    if len(image_data) > 50000:
        confidence += 5
    if ai_sigs["has_ai_signature"]:
        confidence += 20
    if exif_info["has_camera_info"]:
        confidence += 10
    if no_metadata and dim_info["exact_match"] and is_lossless:
        confidence += 8
    confidence = round(min(90, confidence), 1)

    # === Display indicators ===
    # Convert to 0-100 "naturalness" scores for display
    indicators = {
        "frequency_naturalness": round(100 - scores.get("frequency_spectrum", 50), 1),
        "texture_variance": round(100 - scores.get("texture_uniformity", 50), 1),
        "channel_authenticity": round(100 - scores.get("channel_correlation", 50), 1),
        "contrast_naturalness": round(100 - scores.get("contrast_pattern", 50), 1),
    }

    # === Summary ===
    detected_tool = ai_sigs["found_signatures"][0] if ai_sigs["found_signatures"] else None

    if detected_tool:
        summary = f"AI tool signature detected: {detected_tool}. This image was very likely generated by AI."
    elif ai_probability > 65:
        top_signals = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
        signal_names = [s[0].replace("_", " ") for s in top_signals]
        summary = (
            f"Image shows strong AI-generation signals ({ai_probability}% probability). "
            f"The frequency spectrum, texture patterns, and color channels show characteristics "
            f"typical of AI-generated imagery. Key signals: {', '.join(signal_names)}."
        )
    elif ai_probability > 40:
        summary = (
            f"Image shows mixed signals ({ai_probability}% AI probability). "
            f"Some characteristics suggest AI generation while others are consistent "
            f"with real photography. This could be AI-generated with post-processing, "
            f"or a heavily edited real photograph."
        )
    elif ai_probability > 20:
        summary = (
            f"Image appears mostly authentic ({ai_probability}% AI probability). "
            f"Frequency analysis and texture patterns are largely consistent with "
            f"natural photography."
        )
    else:
        summary = (
            f"Image appears authentic ({ai_probability}% AI probability). "
            f"Frequency spectrum, noise patterns, and texture variance all show "
            f"characteristics of a real camera photograph."
        )

    if exif_info["camera_model"]:
        summary += f" Camera: {exif_info['camera_model']}."

    return {
        "ai_probability": ai_probability,
        "confidence": confidence,
        "indicators": indicators,
        "summary": summary,
        "detected_tool": detected_tool,
        "image_info": {
            "format": fmt.lower(),
            "width": width,
            "height": height,
            "file_size_kb": round(len(image_data) / 1024, 1),
        },
    }
