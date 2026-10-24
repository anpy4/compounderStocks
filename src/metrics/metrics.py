from abc import ABC, abstractmethod
from math import isfinite
from statistics import mean
from typing import Tuple, Optional


def finite_number(value) -> Optional[float]:
    """Normalize provider scalars, rejecting missing and non-finite values."""
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if isfinite(number) else None


def statement_value(frame, labels, period) -> Optional[float]:
    """Use the first valid alias in this period; never borrow another year."""
    if period not in frame.columns:
        return None
    for label in labels:
        if label in frame.index:
            value = finite_number(frame.loc[label, period])
            if value is not None:
                return value
    return None


def total_debt(balance_sheet, period) -> Optional[float]:
    """Prefer the reported total; component aliases must not be added twice."""
    debt = statement_value(balance_sheet, ["Total Debt"], period)
    if debt is not None:
        return debt if debt >= 0 else None
    long_term = statement_value(
        balance_sheet, ["Long Term Debt", "Long Term Debt And Capital Lease Obligation"], period
    )
    current = statement_value(
        balance_sheet,
        ["Current Debt", "Current Debt And Capital Lease Obligation", "Short Term Debt", "Short Long Term Debt"],
        period,
    )
    # An absent component is unknown, not evidence of zero borrowings.
    if long_term is None or current is None or long_term < 0 or current < 0:
        return None
    return finite_number(long_term + current)


def is_annual_pair(current, previous) -> bool:
    """Allow 52/53-week fiscal years, but not quarters or missing whole years."""
    return 350 <= (current - previous).days <= 380


def previous_annual_period(frame, period):
    return next(
        (date for date in sorted(frame.columns, reverse=True) if is_annual_pair(period, date)),
        None,
    )


def average_annual_growth(values, *, allow_losses=False) -> Optional[float]:
    """Arithmetic mean of valid adjacent annual changes, not CAGR.

    Percentage growth from a zero/negative base is not economically comparable.
    Missing observations must not create a synthetic multi-year growth rate.
    """
    values = values.sort_index(ascending=False)
    rates = []
    for index in range(len(values) - 1):
        if not is_annual_pair(values.index[index], values.index[index + 1]):
            continue
        current = finite_number(values.iloc[index])
        previous = finite_number(values.iloc[index + 1])
        if current is None or previous is None or previous <= 0:
            continue
        if current < 0 and not allow_losses:
            continue
        rate = finite_number((current - previous) / previous)
        if rate is not None:
            rates.append(rate)
    return finite_number(mean(rates)) if rates else None


class MetricCalculator(ABC):
    @abstractmethod
    def calculate(self, ticker) -> Tuple[Optional[float], str]:
        """Abstract method to calculate the metric."""
        pass

    @abstractmethod
    def classify(self, value: float) -> str:
        """Abstract method to evaluate the metric."""
        pass