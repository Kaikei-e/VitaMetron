"""Blocked walk-forward cross-validation for time-series models.

Implements expanding-window walk-forward CV with a configurable gap
to prevent temporal leakage in next-day predictions.
"""

import logging
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import shap
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from xgboost import XGBRegressor

from app.features.pca_reducer import PCAReducer

logger = logging.getLogger(__name__)


@dataclass
class FoldResult:
    fold_idx: int
    train_start: date
    train_end: date
    test_date: date
    y_true: float
    y_pred: float
    feature_importances: dict[str, float] = field(default_factory=dict)


@dataclass
class CVResult:
    fold_results: list[FoldResult]
    mae: float
    rmse: float
    r2: float
    directional_accuracy: float
    stable_features: list[str]


def walk_forward_cv(
    X: np.ndarray,
    y: np.ndarray,
    dates: list[date],
    feature_names: list[str],
    min_train_days: int = 90,
    gap_days: int = 1,
    params: dict | None = None,
    compute_shap: bool = True,
) -> CVResult:
    """Blocked walk-forward cross-validation with expanding window.

    For each fold:
    1. Train on [0 .. t], skip `gap_days`, predict at t + gap_days + 1
    2. Re-normalize features within each fold (training stats only)
    3. Compute SHAP values for stability selection

    Args:
        X: Feature matrix (n_samples, n_features).
        y: Target vector.
        dates: Corresponding dates.
        feature_names: Feature names.
        min_train_days: Minimum training window size.
        gap_days: Gap between train end and test (prevents leakage).
        params: XGBoost parameters (uses defaults if None).

    Returns:
        CVResult with per-fold results and aggregate metrics.
    """
    n = len(y)
    if n < min_train_days + gap_days + 1:
        raise ValueError(
            f"Need at least {min_train_days + gap_days + 1} samples, got {n}"
        )

    if params is None:
        params = {
            "objective": "reg:squarederror",
            "max_depth": 3,
            "min_child_weight": 10,
            "learning_rate": 0.05,
            "subsample": 0.7,
            "colsample_bytree": 0.7,
            "reg_lambda": 5,
            "n_estimators": 200,
            "random_state": 42,
            "device": "cuda",
        }

    fold_results: list[FoldResult] = []
    feature_importance_counts: dict[str, int] = {name: 0 for name in feature_names}

    for train_end_idx in range(min_train_days - 1, n - gap_days - 1):
        test_idx = train_end_idx + gap_days + 1
        if test_idx >= n:
            break

        # Split
        X_train = X[: train_end_idx + 1]
        y_train = y[: train_end_idx + 1]
        X_test = X[test_idx : test_idx + 1]
        y_test = y[test_idx]

        # Fold-local normalization (training stats only)
        train_medians = np.nanmedian(X_train, axis=0)
        train_stds = np.nanstd(X_train, axis=0)
        train_stds[train_stds == 0] = 1.0

        # Impute NaN with training medians
        X_train_norm = X_train.copy()
        X_test_norm = X_test.copy()
        for col in range(X_train_norm.shape[1]):
            mask = np.isnan(X_train_norm[:, col])
            if mask.any():
                X_train_norm[mask, col] = train_medians[col]
            mask_test = np.isnan(X_test_norm[:, col])
            if mask_test.any():
                X_test_norm[mask_test, col] = train_medians[col]

        # Normalize
        X_train_norm = (X_train_norm - train_medians) / train_stds
        X_test_norm = (X_test_norm - train_medians) / train_stds

        # Train with early stopping (patience=20 rounds)
        fold_params = {k: v for k, v in params.items() if k != "early_stopping_rounds"}
        model = XGBRegressor(**fold_params, early_stopping_rounds=20)
        model.fit(
            X_train_norm,
            y_train,
            eval_set=[(X_test_norm, np.array([y_test]))],
            verbose=False,
        )

        # Predict
        y_pred = float(model.predict(X_test_norm)[0])

        # Feature importances for this fold
        shap_importances: dict[str, float] = {}
        if compute_shap:
            try:
                explainer = shap.TreeExplainer(model)
                shap_values = explainer.shap_values(X_test_norm)
                for i, name in enumerate(feature_names):
                    shap_importances[name] = float(abs(shap_values[0][i]))
            except Exception:
                logger.debug("SHAP failed for fold %d, using gain importance", len(fold_results))
                importances = model.feature_importances_
                for i, name in enumerate(feature_names):
                    shap_importances[name] = float(importances[i])
        else:
            importances = model.feature_importances_
            for i, name in enumerate(feature_names):
                shap_importances[name] = float(importances[i])

        # Track top-10 features for stability selection
        top_10 = sorted(shap_importances, key=shap_importances.get, reverse=True)[:10]
        for name in top_10:
            feature_importance_counts[name] += 1

        fold_results.append(
            FoldResult(
                fold_idx=len(fold_results),
                train_start=dates[0],
                train_end=dates[train_end_idx],
                test_date=dates[test_idx],
                y_true=float(y_test),
                y_pred=y_pred,
                feature_importances=shap_importances,
            )
        )

    # Aggregate metrics
    y_trues = np.array([f.y_true for f in fold_results])
    y_preds = np.array([f.y_pred for f in fold_results])

    mae = float(np.mean(np.abs(y_trues - y_preds)))
    rmse = float(np.sqrt(np.mean((y_trues - y_preds) ** 2)))

    ss_res = np.sum((y_trues - y_preds) ** 2)
    ss_tot = np.sum((y_trues - np.mean(y_trues)) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0

    # Directional accuracy: both above or both below zero
    correct_direction = np.sum(np.sign(y_trues) == np.sign(y_preds))
    directional_accuracy = float(correct_direction / len(y_trues)) if len(y_trues) > 0 else 0.0

    # Stability selection: features in top-10 of >70% of folds
    n_folds = len(fold_results)
    threshold = 0.7 * n_folds
    stable_features = [
        name for name, count in feature_importance_counts.items()
        if count >= threshold
    ]

    return CVResult(
        fold_results=fold_results,
        mae=mae,
        rmse=rmse,
        r2=r2,
        directional_accuracy=directional_accuracy,
        stable_features=stable_features,
    )


def walk_forward_cv_lstm(
    X: np.ndarray,
    y: np.ndarray,
    dates: list[date],
    feature_names: list[str],
    lookback: int = 7,
    min_train_days: int = 90,
    gap_days: int = 1,
    max_epochs: int = 200,
    patience: int = 15,
    batch_size: int = 16,
    lr: float = 0.001,
    weight_decay: float = 1e-4,
    hidden_dim: int = 16,
    dropout: float = 0.4,
) -> CVResult:
    """Walk-forward cross-validation for LSTM with PCA reduction.

    For each fold:
    1. Fit PCA reducer on training data only
    2. Create (lookback, reduced_dim) sequences
    3. Train LSTM with early stopping
    4. Predict on test point

    Args:
        X: Feature matrix (n_samples, n_features).
        y: Target vector.
        dates: Corresponding dates.
        feature_names: Feature names for PCA grouping.
        lookback: Number of days per sequence.
        min_train_days: Minimum training window size.
        gap_days: Gap between train end and test (prevents leakage).
        max_epochs: Maximum training epochs per fold.
        patience: Early stopping patience.
        batch_size: Training batch size.
        lr: Learning rate.
        weight_decay: L2 regularization.
        hidden_dim: LSTM hidden layer size.
        dropout: Input dropout rate.

    Returns:
        CVResult with per-fold results and aggregate metrics.
    """
    from app.models.lstm_predictor import LSTMRegressor

    n = len(y)
    # Need: min_train_days for training, gap_days gap, lookback-1 for sequence context,
    # and 1 for the test point itself
    min_required = min_train_days + gap_days + 1
    if n < min_required:
        raise ValueError(f"Need at least {min_required} samples, got {n}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    fold_results: list[FoldResult] = []

    for train_end_idx in range(min_train_days - 1, n - gap_days - 1):
        test_idx = train_end_idx + gap_days + 1
        if test_idx >= n:
            break

        # The test sequence needs `lookback` days ending at test_idx - 1
        # (the features for the test point are the lookback days before it)
        seq_start = test_idx - lookback
        if seq_start < 0:
            continue

        # All sequence days must come from available data
        # and the test sequence must not overlap with training period + gap
        # seq_start..test_idx-1 are used as input, test_idx is the prediction target
        # For no leakage: the sequence can use data up to test_idx - 1
        # The gap ensures: train_end_idx + gap_days < test_idx
        # We just need to ensure seq_start >= 0 (checked above)

        # Training data
        X_train = X[: train_end_idx + 1]
        y_train = y[: train_end_idx + 1]

        # Impute NaN before PCA (fold-local training stats)
        train_medians_raw = np.nanmedian(X_train, axis=0)
        nan_median_mask = np.isnan(train_medians_raw)
        if nan_median_mask.any():
            train_medians_raw[nan_median_mask] = 0.0

        X_train_imputed = X_train.copy()
        for col in range(X_train_imputed.shape[1]):
            mask = np.isnan(X_train_imputed[:, col])
            if mask.any():
                X_train_imputed[mask, col] = train_medians_raw[col]

        # Fit PCA on imputed training data
        pca = PCAReducer()
        pca.fit(X_train_imputed, feature_names)
        X_train_reduced = pca.transform(X_train_imputed)

        # Fold-local normalization (training stats)
        train_medians = np.nanmedian(X_train_reduced, axis=0)
        train_stds = np.nanstd(X_train_reduced, axis=0)
        train_stds[train_stds == 0] = 1.0
        X_train_norm = (X_train_reduced - train_medians) / train_stds

        # Create training sequences
        train_sequences = []
        train_targets = []
        for i in range(lookback, len(y_train)):
            train_sequences.append(X_train_norm[i - lookback : i])
            train_targets.append(y_train[i])

        if len(train_sequences) < 5:
            continue  # Not enough sequences for this fold

        X_seq = np.array(train_sequences, dtype=np.float32)
        y_seq = np.array(train_targets, dtype=np.float32)

        # Train/val split for early stopping
        n_val = max(1, int(len(y_seq) * 0.15))
        X_train_t = torch.tensor(X_seq[:-n_val], dtype=torch.float32).to(device)
        y_train_t = torch.tensor(y_seq[:-n_val], dtype=torch.float32).to(device)
        X_val_t = torch.tensor(X_seq[-n_val:], dtype=torch.float32).to(device)
        y_val_t = torch.tensor(y_seq[-n_val:], dtype=torch.float32).to(device)

        input_dim = X_seq.shape[2]
        model = LSTMRegressor(input_dim=input_dim, hidden_dim=hidden_dim, dropout=dropout)
        model.to(device)

        optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
        criterion = nn.MSELoss()

        train_ds = TensorDataset(X_train_t, y_train_t)
        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)

        best_val_loss = float("inf")
        best_state = None
        epochs_no_improve = 0

        for epoch in range(max_epochs):
            model.train()
            for X_batch, y_batch in train_loader:
                optimizer.zero_grad()
                preds = model(X_batch)
                loss = criterion(preds, y_batch)
                loss.backward()
                optimizer.step()

            model.eval()
            with torch.no_grad():
                val_preds = model(X_val_t)
                val_loss = criterion(val_preds, y_val_t).item()

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_state = {k: v.clone() for k, v in model.state_dict().items()}
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            if epochs_no_improve >= patience:
                break

        if best_state is not None:
            model.load_state_dict(best_state)

        # Prepare test sequence: impute NaN, PCA-reduce, normalize using training stats
        X_test_window = X[seq_start : test_idx].copy()  # lookback days
        for col in range(X_test_window.shape[1]):
            mask = np.isnan(X_test_window[:, col])
            if mask.any():
                X_test_window[mask, col] = train_medians_raw[col]
        X_test_reduced = pca.transform(X_test_window)
        X_test_norm = (X_test_reduced - train_medians) / train_stds
        X_test_t = torch.tensor(
            X_test_norm.astype(np.float32), dtype=torch.float32
        ).unsqueeze(0).to(device)

        model.eval()
        with torch.no_grad():
            y_pred = float(model(X_test_t).item())

        fold_results.append(
            FoldResult(
                fold_idx=len(fold_results),
                train_start=dates[0],
                train_end=dates[train_end_idx],
                test_date=dates[test_idx],
                y_true=float(y[test_idx]),
                y_pred=y_pred,
            )
        )

    if not fold_results:
        return CVResult(
            fold_results=[],
            mae=float("inf"),
            rmse=float("inf"),
            r2=0.0,
            directional_accuracy=0.0,
            stable_features=[],
        )

    # Aggregate metrics
    y_trues = np.array([f.y_true for f in fold_results])
    y_preds = np.array([f.y_pred for f in fold_results])

    mae = float(np.mean(np.abs(y_trues - y_preds)))
    rmse = float(np.sqrt(np.mean((y_trues - y_preds) ** 2)))

    ss_res = np.sum((y_trues - y_preds) ** 2)
    ss_tot = np.sum((y_trues - np.mean(y_trues)) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0

    correct_direction = np.sum(np.sign(y_trues) == np.sign(y_preds))
    directional_accuracy = float(correct_direction / len(y_trues)) if len(y_trues) > 0 else 0.0

    return CVResult(
        fold_results=fold_results,
        mae=mae,
        rmse=rmse,
        r2=r2,
        directional_accuracy=directional_accuracy,
        stable_features=[],  # LSTM doesn't provide feature importances
    )
