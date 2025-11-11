from abc import ABC, abstractmethod
from typing import Tuple, Optional


class MetricCalculator(ABC):
    @abstractmethod
    def calculate(self, ticker) -> Tuple[Optional[float], str]:
        """Abstract method to calculate the metric."""
        pass

    @abstractmethod
    def classify(self, value: float) -> str:
        """Abstract method to evaluate the metric."""
        pass