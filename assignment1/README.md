# Handwritten Digit Recognition (MNIST) — Logistic Regression

For this assignment I took the Fashion-MNIST logistic regression example we
were given and adapted it to classify handwritten digits (0-9) from the
MNIST dataset instead of clothing items. The model itself stays just as
simple — a single linear layer, no hidden layers, no activation functions —
only the dataset and class labels change.

## How to run it

```bash
pip install -r requirements.txt

# 1. Download and preprocess the dataset, save sample figures
python data_prep.py

# 2. Train the model, evaluate it, save the model + all figures/metrics
python train.py

# 3. Load the saved model and predict WITHOUT retraining
python predict.py --index 0
python predict.py --image path/to/your/digit.png
```

The first time you run `data_prep.py` or `train.py`, it downloads the
dataset through `kagglehub.dataset_download("oddrationale/mnist-in-csv")`,
so you need a Kaggle account with an API token set up locally
(`~/.kaggle/kaggle.json`).

Everything the scripts produce — the trained model, figures, metrics, and
reports — gets saved into `outputs/`.

---

## Dataset and Preprocessing

**How many training and test images are there?**
MNIST comes split into 60,000 training images and 10,000 test images. I
confirmed this by printing the array shapes in `data_prep.py`:
```
Train images shape: (60000, 784)
Train labels shape: (60000,)
Test images shape:  (10000, 784)
Test labels shape:  (10000,)
```
(full output in `outputs/data_shapes.txt`)

**What are the image dimensions and class labels?**
Each image is 28×28 pixels, grayscale. There are 10 classes — the digits 0
through 9.

**Why do we convert each image into 784 values?**
Because the model is just one linear layer, and a linear layer takes a flat
vector as input, not a 2D grid. So instead of feeding in a 28×28 image, we
flatten it into a single row of 28 × 28 = 784 numbers, one per pixel, and
that's what actually goes into the model.

**Why do we divide pixel values by 255?**
The raw pixels are stored as integers from 0 to 255. Dividing everything by
255 squeezes that down to the 0–1 range. Smaller, consistent input values
make the optimizer's job easier — training is faster and more stable than
if we fed in raw 0–255 numbers.

**Why must training and test data remain separate?**
Because the whole point of the test set is to see how the model does on
data it's never seen before. If any test examples leaked into training, the
model could basically memorize them, and the accuracy we report would be
misleadingly high — it wouldn't tell us anything real about how the model
generalizes.

**Figures:**
- Training/test shapes → `outputs/data_shapes.txt`
- One sample image per digit → `outputs/figures/sample_digits.png`

---

## Model and Training

**Why does the model use 784 inputs and 10 outputs?**
784 because that's how many pixels are in one flattened image, and 10
because there are 10 possible digits. Each of the 10 outputs is a raw score
(logit) for one digit class — whichever one comes out highest is the
model's prediction.

**Why do we use CrossEntropyLoss?**
Because this is a multiclass classification problem where each image
belongs to exactly one class. `CrossEntropyLoss` handles the softmax and the
negative log-likelihood calculation together, and it directly pushes the
model to assign a high probability to the correct digit — which is exactly
what we want it optimizing for.

**What batch size, learning rate, and number of epochs did you use?**
I kept it close to the settings from the Fashion-MNIST example:
- Batch size: 64
- Learning rate: 0.0005
- Epochs: 20
- Optimizer: Adam, weight decay 0.0001
- Seed: 42, just so results are reproducible if I re-run it

**How did the training loss change? What does this tell you?**
Looking at `outputs/figures/training_loss.png`, the loss dropped fast in
the first handful of epochs and then kept easing down more gradually,
ending at **0.258** after 20 epochs. That pattern makes sense for a model
this simple — a single linear layer converges quickly because there aren't
many parameters to tune, and it settles into a moderate loss rather than
driving toward zero, since it just doesn't have the capacity to perfectly
separate every digit using only a weighted sum of raw pixels.

**Figures:**
- Model architecture → printed when `train.py` runs (`LogisticRegressionModel(...)`)
- Training settings → listed above, also saved in `outputs/metrics.json`
- Training loss graph → `outputs/figures/training_loss.png`

---

## Evaluation and Predictions

**What test accuracy did you achieve?**
**92.68%** (9,268 / 10,000 correct) on the test set. The one-vs-rest ROC
curves back this up — mean AUC across all 10 digits is **0.9942**, so the
model ranks the correct digit highly even on the cases it doesn't get
exactly right.

**How does it compare with the most-frequent-class baseline?**
The most-frequent-class baseline (always guessing digit `1`, the most
common label in training) gets **11.35%**. So my model beats it by more
than 8x — it's clearly learning real structure from the pixels, not just
guessing the most common digit every time.

**Which digit has the highest recall? Which has the lowest?**
Digit `1` has the highest recall at **98.24%**, with digit `0` close
behind at 97.96%. Digit `5` has the lowest recall at **87.00%** — it's the
only digit under 90%.

**Which digit pairs are frequently confused?**
Adding up both directions of the confusion matrix, the most confused pairs
are:
- **4 ↔ 9** (63 total mix-ups — the single biggest source of confusion, mostly `4`s predicted as `9`, 39 of them)
- **3 ↔ 5** (55 total, mostly `5`s predicted as `3`)
- **7 ↔ 9** (52 total, mostly `7`s predicted as `9`)
- **5 ↔ 8** (50 total, mostly `5`s predicted as `8`)

**What might explain the incorrect predictions?**
A single linear layer just adds up pixel intensities with fixed weights —
it has no real concept of shape, and it can't handle a digit that's
shifted, rotated, or written with a different stroke thickness than usual.
So digits that are written a little unusually, or that happen to overlap
with another digit's typical pixel pattern, are the ones most likely to
get misclassified. That shows up clearly in the three incorrect examples
in `outputs/figures/incorrect_predictions.png`:
- A `5` predicted as `6` — this one's bottom loop is drawn almost fully
  closed, so its pixel pattern ends up looking a lot like a `6`'s loop.
- A `4` predicted as `6` — the top of this `4` is closed into a loop
  instead of staying open, again making it resemble `6`'s loop shape.
- A `3` predicted as `2` — the middle of this `3` is fairly flat with a
  hooked top, so it lacks the usual rounded double-bump that separates a
  `3` from a `2`.

**Does a high test accuracy guarantee correct predictions on camera images? Explain.**
No, not really. Getting 92.68% on the test set doesn't mean much for a real
camera photo. The test accuracy only tells us how well the model does on
images that look like the MNIST training data — centered, cleaned up,
already resized to 28×28. A photo from a real camera is a different story:
different lighting, background clutter, the digit could be off-center or
at an angle, blurry, or a different scale entirely. Unless I preprocess a
camera photo to match MNIST's format almost exactly, this model — being
just a simple linear classifier with no real invariance to shifting or
rotating — probably wouldn't perform nearly as well on it as the reported
test accuracy would suggest.

**Figures:**
- Test and baseline accuracy → `outputs/metrics.json`
- Classification report → `outputs/classification_report.txt`
- Confusion matrix → `outputs/figures/confusion_matrix.png`
- ROC curves (one-vs-rest AUC per digit) → `outputs/figures/roc_curves.png`
- Nine random test predictions (green = correct, red = wrong) → `outputs/figures/sample_predictions.png`
- Three incorrect predictions → `outputs/figures/incorrect_predictions.png` (see explanations above)

---

## Repo layout

```
README.md            this report
data_prep.py          dataset download + preprocessing
train.py              model training + evaluation
predict.py            loads the saved model and predicts without retraining
requirements.txt      python packages needed
outputs/              saved model, figures, and evaluation results
```
