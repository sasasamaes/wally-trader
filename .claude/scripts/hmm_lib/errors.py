"""Custom exceptions for the HMM diagnostic tool."""


class HMMAnalyzeError(Exception):
    """Base class for all HMM analyze errors."""


class FetchError(HMMAnalyzeError):
    """OHLCV fetch failed (network, 4xx, 5xx)."""


class InsufficientDataError(HMMAnalyzeError):
    """Fewer bars returned than required minimum (1000)."""


class HMMFitError(HMMAnalyzeError):
    """All K values failed to fit a usable HMM."""


class StrategyExecError(HMMAnalyzeError):
    """A strategy raised an exception during backtest. Attributes: bar_index, symbol, strategy."""

    def __init__(self, message: str, *, bar_index: int, symbol: str, strategy: str):
        super().__init__(message)
        self.bar_index = bar_index
        self.symbol = symbol
        self.strategy = strategy
