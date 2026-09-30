"""Download and preprocess the MNIST handwritten digit dataset.

Source: Kaggle dataset "oddrationale/mnist-in-csv", which provides MNIST as
mnist_train.csv / mnist_test.csv (first column = label, remaining 784 columns
= pixel values 0-255).
"""

from pathlib import Path
from typing import Optional, Tuple

import kagglehub
import numpy as np
import pandas as pd

IMAGE_SIZE = 28
NUM_PIXELS = IMAGE_SIZE * IMAGE_SIZE  # 28 * 28 = 784
CLASS_LABELS = [str(i) for i in range(10)]  # digits 0-9


def download_dataset() -> Path:
    """Download (or reuse the local cache of) the MNIST CSV dataset from Kaggle."""
    return Path(kagglehub.dataset_download("oddrationale/mnist-in-csv"))


def _load_csv(csv_path: Path):
    """Load one MNIST CSV, validate it, and normalize pixel values to [0, 1]."""
    if not csv_path.is_file():
        raise FileNotFoundError(f"Could not find dataset file: {csv_path}")

    df = pd.read_csv(csv_path)
    if "label" not in df.columns or df.shape[1] != NUM_PIXELS + 1:
        raise ValueError(
            f"{csv_path.name} must contain a label column and {NUM_PIXELS} pixel columns."
        )
    if df.empty:
        raise ValueError(f"{csv_path.name} contains no data.")
    if not df["label"].isin(range(10)).all():
        raise ValueError(f"{csv_path.name} contains invalid class labels.")

    pixel_columns = df.drop(columns="label")
    pixels = pixel_columns.to_numpy(dtype=np.float32)
    labels = df["label"].to_numpy(dtype=np.int64)

    if not np.isfinite(pixels).all() or pixels.min() < 0 or pixels.max() > 255:
        raise ValueError(
            f"{csv_path.name} must contain pixel values from 0 to 255 "
            "with no missing or infinite values."
        )
    pixels = pixels / 255.0  # normalize pixel intensity from [0, 255] to [0, 1]
    return pixels, labels, pixel_columns.columns


def load_data(data_dir: Optional[Path] = None):
    """Load MNIST train/test CSVs and normalize pixel values.

    Returns:
        train_images: (60000, 784) float32 in [0, 1]
        train_labels: (60000,) int64 in [0, 9]
        test_images:  (10000, 784) float32 in [0, 1]
        test_labels:  (10000,) int64 in [0, 9]
    """
    if data_dir is None:
        data_dir = download_dataset()

    train_images, train_labels, train_columns = _load_csv(data_dir / "mnist_train.csv")
    test_images, test_labels, test_columns = _load_csv(data_dir / "mnist_test.csv")

    if not train_columns.equals(test_columns):
        raise ValueError("Training and test pixel columns must have the same order.")

    return train_images, train_labels, test_images, test_labels


def validate_data(train_images, train_labels, test_images, test_labels) -> None:
    assert train_images.shape[1] == NUM_PIXELS, "Expected 784 pixel columns in train set"
    assert test_images.shape[1] == NUM_PIXELS, "Expected 784 pixel columns in test set"
    assert train_images.shape[0] == train_labels.shape[0]
    assert test_images.shape[0] == test_labels.shape[0]
    assert float(train_images.min()) >= 0.0 and float(train_images.max()) <= 1.0
    assert set(np.unique(train_labels)).issubset(set(range(10)))
    assert set(np.unique(test_labels)).issubset(set(range(10)))


def save_sample_grid(train_images, train_labels, out_path: Path) -> None:
    """Save one labeled sample image per digit (0-9)."""
    import matplotlib.pyplot as plt

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 5, figsize=(10, 4))
    for digit in range(10):
        idx = int(np.where(train_labels == digit)[0][0])
        ax = axes[digit // 5, digit % 5]
        ax.imshow(train_images[idx].reshape(IMAGE_SIZE, IMAGE_SIZE), cmap="gray")
        ax.set_title(f"Label: {digit}")
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main() -> None:
    out_dir = Path("outputs")
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    data_dir = download_dataset()
    print(f"Dataset downloaded to: {data_dir}")

    train_images, train_labels, test_images, test_labels = load_data(data_dir)
    validate_data(train_images, train_labels, test_images, test_labels)

    print(f"Train images shape: {train_images.shape}, labels shape: {train_labels.shape}")
    print(f"Test images shape:  {test_images.shape}, labels shape: {test_labels.shape}")
    print(f"Class labels: {CLASS_LABELS}")

    shapes_path = out_dir / "data_shapes.txt"
    shapes_path.write_text(
        f"Train images shape: {train_images.shape}\n"
        f"Train labels shape: {train_labels.shape}\n"
        f"Test images shape:  {test_images.shape}\n"
        f"Test labels shape:  {test_labels.shape}\n"
        f"Class labels: {CLASS_LABELS}\n"
    )
    print(f"Saved shape summary to: {shapes_path}")

    sample_path = fig_dir / "sample_digits.png"
    save_sample_grid(train_images, train_labels, sample_path)
    print(f"Saved one sample image per digit to: {sample_path}")


if __name__ == "__main__":
    main()
