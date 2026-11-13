"""Deterministic test-time perturbations for robustness analysis."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import rotate


def add_gaussian_noise(images: np.ndarray, sigma: float, seed: int = 2026) -> np.ndarray:
    rng = np.random.default_rng(seed)
    noisy = images + rng.normal(0.0, sigma, size=images.shape).astype(np.float32)
    return np.clip(noisy, 0.0, 1.0).astype(np.float32)


def change_contrast(images: np.ndarray, scale: float) -> np.ndarray:
    contrasted = (images - 0.5) * scale + 0.5
    return np.clip(contrasted, 0.0, 1.0).astype(np.float32)


def translate(images: np.ndarray, dy: int, dx: int) -> np.ndarray:
    translated = np.zeros_like(images)
    src_y0, src_y1 = max(0, -dy), min(16, 16 - dy)
    src_x0, src_x1 = max(0, -dx), min(16, 16 - dx)
    dst_y0, dst_y1 = max(0, dy), min(16, 16 + dy)
    dst_x0, dst_x1 = max(0, dx), min(16, 16 + dx)
    translated[:, dst_y0:dst_y1, dst_x0:dst_x1] = images[
        :, src_y0:src_y1, src_x0:src_x1
    ]
    return translated


def rotate_images(images: np.ndarray, angle: float) -> np.ndarray:
    return np.stack(
        [
            np.clip(
                rotate(img, angle=angle, reshape=False, order=1, mode="constant", cval=0.0),
                0.0,
                1.0,
            )
            for img in images
        ]
    ).astype(np.float32)
