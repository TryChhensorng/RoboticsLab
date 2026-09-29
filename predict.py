"""Load the trained MNIST logistic regression model and predict without retraining.

Usage:
    python predict.py --index 42
    python predict.py --image path/to/digit.png
"""

import argparse
from pathlib import Path

import numpy as np
import torch

from data_prep import IMAGE_SIZE, load_data
from train import MODEL_PATH, LogisticRegressionModel, device

CLASS_LABELS = [str(i) for i in range(10)]


def load_trained_model(model_path: Path = MODEL_PATH) -> LogisticRegressionModel:
    model = LogisticRegressionModel().to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()
    return model


@torch.no_grad()
def predict_array(model, pixels: np.ndarray):
    """pixels: (784,) or (N, 784) float32 array normalized to [0, 1]."""
    if pixels.ndim == 1:
        pixels = pixels[None, :]
    x = torch.from_numpy(pixels.astype(np.float32)).to(device)
    logits = model(x)
    probs = torch.softmax(logits, dim=1)
    preds = torch.argmax(probs, dim=1)
    return preds.cpu().numpy(), probs.cpu().numpy()


def load_image_file(image_path: Path) -> np.ndarray:
    """Load an arbitrary image file, convert to 28x28 grayscale, normalize to [0, 1].

    Note: a real camera photo is NOT drawn from the same distribution as MNIST
    (different lighting, framing, stroke width, background) so this preprocessing
    alone does not guarantee accurate predictions -- see README for discussion.
    """
    from PIL import Image

    img = Image.open(image_path).convert("L").resize((IMAGE_SIZE, IMAGE_SIZE))
    pixels = np.asarray(img, dtype=np.float32).reshape(-1) / 255.0
    return pixels


def main():
    parser = argparse.ArgumentParser(description="Predict MNIST digit(s) with the trained model.")
    parser.add_argument("--index", type=int, default=None, help="Index into the MNIST test set to predict.")
    parser.add_argument("--image", type=str, default=None, help="Path to a custom image file to classify.")
    args = parser.parse_args()

    model = load_trained_model()

    if args.image:
        pixels = load_image_file(Path(args.image))
        preds, probs = predict_array(model, pixels)
        print(f"Image: {args.image}")
        print(f"Predicted digit: {preds[0]} (confidence: {probs[0, preds[0]]:.4f})")
        return

    _, _, test_images, test_labels = load_data()
    idx = args.index if args.index is not None else 0
    preds, probs = predict_array(model, test_images[idx])
    print(f"Test index: {idx}")
    print(f"True label: {test_labels[idx]}")
    print(f"Predicted digit: {preds[0]} (confidence: {probs[0, preds[0]]:.4f})")


if __name__ == "__main__":
    main()
