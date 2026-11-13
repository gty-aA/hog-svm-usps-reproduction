"""Small, dependency-light HOG implementation used by the reproduction.

The implementation follows the classical Dalal--Triggs design:
unsigned orientation bins, bilinear orientation interpolation,
2x2-cell blocks and L2-Hys block normalisation.
"""

from __future__ import annotations

import numpy as np


def load_usps(path: str) -> tuple[np.ndarray, np.ndarray]:
    """Load a LIBSVM-formatted USPS split into images and 0--9 labels."""
    import bz2

    features = []
    labels = []
    with bz2.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            fields = line.strip().split()
            if not fields:
                continue
            label = int(float(fields[0])) % 10
            row = np.zeros(256, dtype=np.float32)
            for item in fields[1:]:
                index_text, value_text = item.split(":")
                row[int(index_text) - 1] = float(value_text)
            # USPS values are approximately in [-1, 1].
            features.append(((row + 1.0) * 0.5).reshape(16, 16))
            labels.append(label)
    return np.asarray(features, dtype=np.float32), np.asarray(labels, dtype=np.int64)


def _gradients(image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    image = np.asarray(image, dtype=np.float32)
    gx = np.zeros_like(image)
    gy = np.zeros_like(image)
    gx[:, 1:-1] = image[:, 2:] - image[:, :-2]
    gy[1:-1, :] = image[2:, :] - image[:-2, :]
    return gx, gy


def hog_descriptor(
    image: np.ndarray,
    cell_size: int = 4,
    bins: int = 9,
    block_size: int = 2,
    epsilon: float = 1e-6,
) -> np.ndarray:
    """Compute an L2-Hys normalised HOG descriptor for a 16x16 image."""
    image = np.asarray(image, dtype=np.float32)
    if image.shape != (16, 16):
        raise ValueError(f"Expected a 16x16 image, got {image.shape}")
    if 16 % cell_size != 0:
        raise ValueError("cell_size must divide 16")

    gx, gy = _gradients(image)
    magnitude = np.hypot(gx, gy)
    # atan2 returns [-pi, pi]; unsigned orientation folds onto [0, pi).
    orientation = np.mod(np.arctan2(gy, gx), np.pi)
    bin_position = orientation / np.pi * bins - 0.5
    lower = np.floor(bin_position).astype(np.int32)
    upper = (lower + 1) % bins
    alpha = bin_position - np.floor(bin_position)

    cells_per_side = 16 // cell_size
    hist = np.zeros((cells_per_side, cells_per_side, bins), dtype=np.float32)
    for cy in range(cells_per_side):
        for cx in range(cells_per_side):
            y0, y1 = cy * cell_size, (cy + 1) * cell_size
            x0, x1 = cx * cell_size, (cx + 1) * cell_size
            mag = magnitude[y0:y1, x0:x1].ravel()
            low = lower[y0:y1, x0:x1].ravel()
            high = upper[y0:y1, x0:x1].ravel()
            a = alpha[y0:y1, x0:x1].ravel()
            np.add.at(hist[cy, cx], low, mag * (1.0 - a))
            np.add.at(hist[cy, cx], high, mag * a)

    blocks = []
    step = block_size
    for by in range(cells_per_side - block_size + 1):
        for bx in range(cells_per_side - block_size + 1):
            vector = hist[by : by + block_size, bx : bx + block_size].ravel()
            vector = vector / np.sqrt(np.sum(vector * vector) + epsilon * epsilon)
            vector = np.minimum(vector, 0.2)
            vector = vector / np.sqrt(np.sum(vector * vector) + epsilon * epsilon)
            blocks.append(vector)
    return np.concatenate(blocks).astype(np.float32)


def extract_hog(images: np.ndarray, **kwargs) -> np.ndarray:
    return np.stack([hog_descriptor(image, **kwargs) for image in images])


def visualise_hog(
    image: np.ndarray,
    cell_size: int = 4,
    bins: int = 9,
) -> tuple[np.ndarray, np.ndarray]:
    """Return magnitude and orientation maps for explanatory figures."""
    gx, gy = _gradients(image)
    magnitude = np.hypot(gx, gy)
    orientation = np.mod(np.arctan2(gy, gx), np.pi)
    return magnitude, orientation
