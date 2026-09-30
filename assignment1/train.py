"""Train and evaluate a multiclass logistic regression model on MNIST digits."""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import torch
from sklearn.dummy import DummyClassifier
from sklearn.metrics import auc, classification_report, confusion_matrix, roc_curve
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from assignment1.data_prep import CLASS_LABELS, IMAGE_SIZE, NUM_PIXELS, load_data, validate_data

torch.manual_seed(42)

BATCH_SIZE = 64
LEARNING_RATE = 0.0005
NUM_EPOCHS = 20
WEIGHT_DECAY = 0.0001

OUT_DIR = Path("outputs")
FIG_DIR = OUT_DIR / "figures"
MODEL_PATH = OUT_DIR / "model.pth"

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class LogisticRegressionModel(nn.Module):
    """Single linear layer: no hidden layers, no activation functions."""

    def __init__(self, num_inputs: int = NUM_PIXELS, num_classes: int = 10):
        super().__init__()
        self.linear = nn.Linear(num_inputs, num_classes)

    def forward(self, x):
        return self.linear(x)


def make_loaders(train_images, train_labels, test_images, test_labels):
    train_ds = TensorDataset(torch.from_numpy(train_images), torch.from_numpy(train_labels))
    test_ds = TensorDataset(torch.from_numpy(test_images), torch.from_numpy(test_labels))
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False)
    return train_loader, test_loader


def train_model(model, train_loader):
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)

    epoch_losses = []
    model.train()
    for epoch in range(1, NUM_EPOCHS + 1):
        running_loss = 0.0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            logits = model(images)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * images.size(0)
        epoch_loss = running_loss / len(train_loader.dataset)
        epoch_losses.append(epoch_loss)
        print(f"Epoch {epoch:2d}/{NUM_EPOCHS} - loss: {epoch_loss:.4f}")
    return epoch_losses


def plot_loss(epoch_losses, out_path: Path):
    plt.figure(figsize=(6, 4))
    plt.plot(range(1, len(epoch_losses) + 1), epoch_losses, marker="o")
    plt.xlabel("Epoch")
    plt.ylabel("Training loss (CrossEntropy)")
    plt.title("Training loss over epochs")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


@torch.no_grad()
def evaluate(model, test_loader):
    model.eval()
    all_preds, all_labels, all_probs = [], [], []
    for images, labels in test_loader:
        images = images.to(device)
        logits = model(images)
        probs = torch.softmax(logits, dim=1)
        preds = torch.argmax(probs, dim=1)
        all_preds.append(preds.cpu().numpy())
        all_labels.append(labels.numpy())
        all_probs.append(probs.cpu().numpy())
    return np.concatenate(all_preds), np.concatenate(all_labels), np.concatenate(all_probs)


def most_frequent_baseline(train_images, train_labels, test_images, test_labels):
    baseline = DummyClassifier(strategy="most_frequent")
    baseline.fit(train_images, train_labels)
    baseline_preds = baseline.predict(test_images)
    baseline_acc = float((baseline_preds == test_labels).mean())
    majority_class = int(baseline.classes_[np.argmax(baseline.class_prior_)])
    return majority_class, baseline_acc


def save_confusion_matrix(cm, out_path: Path):
    plt.figure(figsize=(9, 8))
    sns.heatmap(
        cm, annot=True, fmt="d", cmap="Blues",
        xticklabels=CLASS_LABELS, yticklabels=CLASS_LABELS,
    )
    plt.xlabel("Predicted label")
    plt.ylabel("True label")
    plt.title("Confusion matrix")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


def save_roc_curves(all_labels, all_probs, out_path: Path):
    plt.figure(figsize=(9, 8))
    class_aucs = []
    for class_id, class_name in enumerate(CLASS_LABELS):
        binary_targets = (all_labels == class_id).astype(int)
        if np.unique(binary_targets).size < 2:
            continue
        fpr, tpr, _ = roc_curve(binary_targets, all_probs[:, class_id])
        class_auc = auc(fpr, tpr)
        class_aucs.append(class_auc)
        plt.plot(fpr, tpr, label=f"{class_name}: AUC = {class_auc:.3f}")
    plt.plot([0, 1], [0, 1], "k--", label="Random ranking")
    plt.xlabel("False positive rate")
    plt.ylabel("True positive rate")
    plt.title("ROC curves: one class versus rest")
    plt.legend(loc="lower right", fontsize=9)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    return float(np.mean(class_aucs)) if class_aucs else None


def save_sample_predictions(test_images, all_labels, all_preds, out_path: Path, n=9, seed=0):
    rng = np.random.default_rng(seed)
    idxs = rng.choice(len(test_images), size=n, replace=False)
    fig, axes = plt.subplots(3, 3, figsize=(7, 7))
    for ax, idx in zip(axes.flat, idxs):
        ax.imshow(test_images[idx].reshape(IMAGE_SIZE, IMAGE_SIZE), cmap="gray")
        correct = all_labels[idx] == all_preds[idx]
        ax.set_title(
            f"True: {all_labels[idx]} / Pred: {all_preds[idx]}",
            color="green" if correct else "red",
        )
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def save_incorrect_predictions(test_images, all_labels, all_preds, out_path: Path, n=3):
    wrong_idxs = np.where(all_labels != all_preds)[0]
    n = min(n, len(wrong_idxs))
    if n == 0:
        return []
    fig, axes = plt.subplots(1, n, figsize=(4 * n, 4))
    axes = np.atleast_1d(axes)
    for ax, idx in zip(axes, wrong_idxs[:n]):
        ax.imshow(test_images[idx].reshape(IMAGE_SIZE, IMAGE_SIZE), cmap="gray")
        ax.set_title(f"True: {all_labels[idx]} / Pred: {all_preds[idx]}")
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return wrong_idxs[:n].tolist()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    train_images, train_labels, test_images, test_labels = load_data()
    validate_data(train_images, train_labels, test_images, test_labels)

    train_loader, test_loader = make_loaders(train_images, train_labels, test_images, test_labels)

    model = LogisticRegressionModel().to(device)
    print(model)

    epoch_losses = train_model(model, train_loader)
    plot_loss(epoch_losses, FIG_DIR / "training_loss.png")

    torch.save(model.state_dict(), MODEL_PATH)
    print(f"Saved trained model to: {MODEL_PATH}")

    preds, labels, probs = evaluate(model, test_loader)
    test_accuracy = float((preds == labels).mean())
    majority_class, baseline_acc = most_frequent_baseline(
        train_images, train_labels, test_images, test_labels
    )

    report = classification_report(labels, preds, target_names=CLASS_LABELS, digits=4)
    cm = confusion_matrix(labels, preds)

    print(f"Test accuracy: {test_accuracy:.4f}")
    print(f"Most-frequent-class baseline (class {majority_class}): {baseline_acc:.4f}")
    print(report)

    (OUT_DIR / "classification_report.txt").write_text(report)
    save_confusion_matrix(cm, FIG_DIR / "confusion_matrix.png")
    mean_auc = save_roc_curves(labels, probs, FIG_DIR / "roc_curves.png")
    if mean_auc is not None:
        print(f"Mean one-vs-rest AUC: {mean_auc:.4f}")
    save_sample_predictions(test_images, labels, preds, FIG_DIR / "sample_predictions.png")
    wrong_idxs = save_incorrect_predictions(test_images, labels, preds, FIG_DIR / "incorrect_predictions.png")

    metrics = {
        "test_accuracy": test_accuracy,
        "baseline_majority_class": majority_class,
        "baseline_accuracy": baseline_acc,
        "mean_roc_auc": mean_auc,
        "num_epochs": NUM_EPOCHS,
        "batch_size": BATCH_SIZE,
        "learning_rate": LEARNING_RATE,
        "weight_decay": WEIGHT_DECAY,
        "final_training_loss": epoch_losses[-1],
        "confusion_matrix": cm.tolist(),
        "sample_incorrect_indices": wrong_idxs,
    }
    with open(OUT_DIR / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Saved metrics to: {OUT_DIR / 'metrics.json'}")


if __name__ == "__main__":
    main()
