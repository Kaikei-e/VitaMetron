"""LSTM HRV prediction model.

Predicts next-morning HRV Z-score from a 7-day lookback window of
PCA-reduced biometric features. Designed as a lightweight complement
to the XGBoost model for ensemble use.
"""

import json
import logging
import time
from datetime import date
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from app.features.pca_reducer import PCAReducer

logger = logging.getLogger(__name__)


class LSTMRegressor(nn.Module):
    """Single-layer LSTM for time-series regression (~2,700 params)."""

    def __init__(self, input_dim: int, hidden_dim: int = 16, dropout: float = 0.4):
        super().__init__()
        self.input_dropout = nn.Dropout(dropout)
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers=1, batch_first=True)
        self.fc = nn.Linear(hidden_dim, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq_len, input_dim)
        x = self.input_dropout(x)
        _, (h_n, _) = self.lstm(x)  # h_n: (1, batch, hidden)
        out = self.fc(h_n.squeeze(0))  # (batch, 1)
        return out.squeeze(-1)


def _create_sequences(
    X: np.ndarray, y: np.ndarray, lookback: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Create lookback-window sequences from time-ordered features.

    Args:
        X: Feature matrix (n_samples, n_features), time-ordered.
        y: Target vector (n_samples,).
        lookback: Number of past days per sequence.

    Returns:
        (X_seq, y_seq, indices) where:
        - X_seq: (n_valid, lookback, n_features)
        - y_seq: (n_valid,)
        - indices: original indices of the target day for each sequence
    """
    sequences = []
    targets = []
    indices = []
    for i in range(lookback, len(y)):
        sequences.append(X[i - lookback : i])
        targets.append(y[i])
        indices.append(i)
    return (
        np.array(sequences, dtype=np.float32),
        np.array(targets, dtype=np.float32),
        np.array(indices),
    )


class LSTMHRVPredictor:
    """LSTM predictor for next-morning HRV Z-score."""

    def __init__(self, model_store_path: str):
        self._store = Path(model_store_path)
        self._model: LSTMRegressor | None = None
        self._pca_reducer: PCAReducer | None = None
        self._feature_medians: np.ndarray | None = None
        self._feature_stds: np.ndarray | None = None
        self._model_version: str = ""
        self._cv_metrics: dict = {}
        self._input_dim: int = 0
        self._lookback_days: int = 7
        self._training_days: int = 0
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    @property
    def model_version(self) -> str:
        return self._model_version

    @property
    def cv_metrics(self) -> dict:
        return self._cv_metrics

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: list[str],
        dates: list[date],
        lookback_days: int = 7,
        max_epochs: int = 200,
        patience: int = 15,
        batch_size: int = 16,
        lr: float = 0.001,
        weight_decay: float = 1e-4,
    ) -> dict:
        """Train LSTM on PCA-reduced sequences.

        Args:
            X: Feature matrix (n_samples, n_features). May contain NaN.
            y: Target vector.
            feature_names: Feature names.
            dates: Corresponding dates.
            lookback_days: Days in the lookback window.
            max_epochs: Maximum training epochs.
            patience: Early stopping patience.
            batch_size: Training batch size.
            lr: Learning rate.
            weight_decay: L2 regularization.

        Returns:
            Training metadata dict.
        """
        self._lookback_days = lookback_days
        self._training_days = X.shape[0]

        # Fit PCA reducer
        self._pca_reducer = PCAReducer()
        self._pca_reducer.fit(X, feature_names)
        X_reduced = self._pca_reducer.transform(X)

        # Compute normalization stats on reduced features
        self._feature_medians = np.nanmedian(X_reduced, axis=0)
        self._feature_stds = np.nanstd(X_reduced, axis=0)
        self._feature_stds[self._feature_stds == 0] = 1.0

        # Normalize
        X_norm = (X_reduced - self._feature_medians) / self._feature_stds

        # Create sequences
        X_seq, y_seq, _ = _create_sequences(X_norm, y, lookback_days)

        if len(y_seq) < 10:
            raise ValueError(
                f"Too few sequences after windowing: {len(y_seq)} (need >= 10)"
            )

        # Train/val split (last 15% for early stopping)
        n_val = max(1, int(len(y_seq) * 0.15))
        X_train_t = torch.tensor(X_seq[:-n_val], dtype=torch.float32).to(self._device)
        y_train_t = torch.tensor(y_seq[:-n_val], dtype=torch.float32).to(self._device)
        X_val_t = torch.tensor(X_seq[-n_val:], dtype=torch.float32).to(self._device)
        y_val_t = torch.tensor(y_seq[-n_val:], dtype=torch.float32).to(self._device)

        self._input_dim = X_seq.shape[2]
        self._model = LSTMRegressor(input_dim=self._input_dim)
        self._model.to(self._device)

        optimizer = torch.optim.Adam(
            self._model.parameters(), lr=lr, weight_decay=weight_decay
        )
        criterion = nn.MSELoss()

        train_ds = TensorDataset(X_train_t, y_train_t)
        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)

        best_val_loss = float("inf")
        best_state = None
        epochs_no_improve = 0

        for epoch in range(max_epochs):
            self._model.train()
            for X_batch, y_batch in train_loader:
                X_batch = X_batch.to(self._device)
                y_batch = y_batch.to(self._device)
                optimizer.zero_grad()
                preds = self._model(X_batch)
                loss = criterion(preds, y_batch)
                loss.backward()
                optimizer.step()

            # Validation
            self._model.eval()
            with torch.no_grad():
                val_preds = self._model(X_val_t)
                val_loss = criterion(val_preds, y_val_t).item()

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_state = {k: v.clone() for k, v in self._model.state_dict().items()}
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            if epochs_no_improve >= patience:
                logger.debug("Early stopping at epoch %d", epoch + 1)
                break

        # Restore best weights
        if best_state is not None:
            self._model.load_state_dict(best_state)

        self._model_version = f"lstm_v{int(time.time())}"

        n_params = sum(p.numel() for p in self._model.parameters())
        metadata = {
            "model_version": self._model_version,
            "training_days": self._training_days,
            "n_sequences": len(y_seq),
            "lookback_days": lookback_days,
            "input_dim": self._input_dim,
            "n_params": n_params,
            "best_val_loss": best_val_loss,
            "pca_n_features_out": self._pca_reducer.n_features_out,
        }

        logger.info(
            "Trained LSTM: %d sequences, %d params, val_loss=%.4f",
            len(y_seq),
            n_params,
            best_val_loss,
        )

        return metadata

    def predict(self, X_sequence: np.ndarray) -> tuple[float, float]:
        """Predict from a PCA-reduced, normalized sequence.

        Args:
            X_sequence: (lookback, reduced_dim) array, already PCA-reduced and normalized.

        Returns:
            (predicted_z_score, confidence).
        """
        if self._model is None:
            raise RuntimeError("LSTM model not trained or loaded")

        self._model.eval()
        with torch.no_grad():
            x = torch.tensor(X_sequence, dtype=torch.float32).unsqueeze(0).to(self._device)
            z_score = float(self._model(x).item())

        # Confidence: inverse sigmoid of absolute prediction
        # Large predictions get lower confidence (extreme predictions less certain)
        confidence = float(1.0 / (1.0 + 0.3 * abs(z_score)))
        confidence = max(0.0, min(1.0, confidence))

        return z_score, confidence

    def prepare_sequence(self, features_list: list[np.ndarray]) -> np.ndarray | None:
        """Prepare a sequence from raw feature vectors.

        Applies PCA reduction and normalization to a list of daily feature vectors.

        Args:
            features_list: List of lookback_days raw feature vectors (1D arrays).

        Returns:
            (lookback, reduced_dim) array ready for predict(), or None if invalid.
        """
        if self._pca_reducer is None or self._feature_medians is None:
            return None

        if len(features_list) != self._lookback_days:
            return None

        reduced = []
        for feat in features_list:
            if feat is None:
                return None
            r = self._pca_reducer.transform(feat)
            reduced.append(r)

        X_reduced = np.array(reduced, dtype=np.float64)
        X_norm = (X_reduced - self._feature_medians) / self._feature_stds
        return X_norm.astype(np.float32)

    def save(self) -> str:
        """Persist LSTM model artifacts to disk."""
        self._store.mkdir(parents=True, exist_ok=True)

        if self._model is not None:
            torch.save(self._model.state_dict(), self._store / "lstm_hrv.pt")

        if self._pca_reducer is not None:
            self._pca_reducer.save(self._store)

        np.savez(
            self._store / "lstm_scaler.npz",
            feature_medians=self._feature_medians,
            feature_stds=self._feature_stds,
        )

        config = {
            "model_version": self._model_version,
            "input_dim": self._input_dim,
            "lookback_days": self._lookback_days,
            "training_days": self._training_days,
            "cv_metrics": self._cv_metrics,
        }
        (self._store / "lstm_config.json").write_text(json.dumps(config))

        logger.info("Saved LSTM model: %s", self._model_version)
        return self._model_version

    def load(self) -> bool:
        """Load LSTM model artifacts from disk."""
        model_path = self._store / "lstm_hrv.pt"
        config_path = self._store / "lstm_config.json"
        scaler_path = self._store / "lstm_scaler.npz"

        if not all(p.exists() for p in [model_path, config_path, scaler_path]):
            logger.info("No LSTM model found at %s", self._store)
            return False

        try:
            config = json.loads(config_path.read_text())
            self._model_version = config["model_version"]
            self._input_dim = config["input_dim"]
            self._lookback_days = config["lookback_days"]
            self._training_days = config.get("training_days", 0)
            self._cv_metrics = config.get("cv_metrics", {})

            scaler = np.load(scaler_path)
            self._feature_medians = scaler["feature_medians"]
            self._feature_stds = scaler["feature_stds"]

            self._pca_reducer = PCAReducer()
            if not self._pca_reducer.load(self._store):
                logger.warning("Failed to load PCA reducer for LSTM")
                return False

            self._model = LSTMRegressor(input_dim=self._input_dim)
            self._model.load_state_dict(
                torch.load(model_path, map_location=self._device, weights_only=True)
            )
            self._model.to(self._device)
            self._model.eval()

            logger.info("Loaded LSTM model: %s", self._model_version)
            return True
        except Exception:
            logger.exception("Failed to load LSTM model")
            return False
