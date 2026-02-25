"""Training-specific error types."""


class InsufficientDataError(Exception):
    """Raised when there is not enough data to train a model."""

    def __init__(self, model: str, available: int, required: int):
        self.model = model
        self.available = available
        self.required = required
        super().__init__(
            f"{model}: insufficient data — {available} available, {required} required"
        )


class NoNewDataError(Exception):
    """Raised when no new data has been added since the last training."""

    def __init__(self, model: str):
        self.model = model
        super().__init__(f"{model}: no new data since last training")


class LowQualityDataError(Exception):
    """Raised when recent data quality is too low for meaningful retraining."""

    def __init__(self, model: str, valid_days: int, avg_completeness: float):
        self.model = model
        self.valid_days = valid_days
        self.avg_completeness = avg_completeness
        super().__init__(
            f"{model}: low recent quality — {valid_days} valid days, "
            f"{avg_completeness:.0f}% avg completeness in last 7 days"
        )
