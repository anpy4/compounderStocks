from typing import Tuple, Optional
from src.thresholds import SCHWELLENWERTE
from src.metrics.metrics import (
    MetricCalculator, finite_number, previous_annual_period, statement_value,
)


class ROECalculator(MetricCalculator):
    def calculate(self, ticker) -> Tuple[Optional[float], str]:
        """Provider TTM ROE, or annual net income / average shareholders' equity."""
        try:
            try:
                roe = finite_number(ticker.info.get('returnOnEquity'))
            except Exception:
                roe = None  # A failed info endpoint must not disable the fallback.
            if roe is not None:
                return roe, self.classify(roe)

            financials = ticker.financials
            balance_sheet = ticker.balance_sheet
            if financials.empty or balance_sheet.empty:
                return None, "Keine Daten verfügbar"

            period = max(financials.columns)
            previous = previous_annual_period(balance_sheet, period)
            if period not in balance_sheet.columns or previous is None:
                return None, "Nicht genügend passende Eigenkapitalperioden"
            net_income = statement_value(financials, [
                'Net Income Common Stockholders', 'Net Income',
            ], period)
            if net_income is None:
                return None, "Nettogewinn nicht verfügbar"

            equity_current = equity_previous = None
            for key in [
                'Total Stockholder Equity',
                'Stockholders Equity',
                'Common Stock Equity',
            ]:
                current = statement_value(balance_sheet, [key], period)
                opening = statement_value(balance_sheet, [key], previous)
                if current is not None and opening is not None:
                    equity_current, equity_previous = current, opening
                    break
            if (equity_current is None or equity_previous is None
                    or equity_current <= 0 or equity_previous <= 0):
                return None, "Ungültiges Eigenkapital"
            avg_equity = equity_current / 2 + equity_previous / 2
            roe = finite_number(net_income / avg_equity)
            if roe is None:
                return None, "ROE nicht berechenbar"
            return roe, self.classify(roe)
        except Exception as e:
            return None, f"Fehler bei ROE-Berechnung: {str(e)}"

    def classify(self, value: float) -> str:
        if value >= SCHWELLENWERTE['ROE_exzellent']:
            return "Exzellent"
        elif value >= SCHWELLENWERTE['ROE_min']:
            return "Gut"
        else:
            return "Schwach"