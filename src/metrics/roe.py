from typing import Tuple, Optional
from src.thresholds import SCHWELLENWERTE
from src.metrics.metrics import MetricCalculator


class ROECalculator(MetricCalculator):
    def calculate(self, ticker) -> Tuple[Optional[float], str]:
        # Implementation of ROE calculation
        try:
            if hasattr(ticker, 'info') and 'returnOnEquity' in ticker.info:
                roe = ticker.info['returnOnEquity']
                if roe is not None:
                    return roe, self.classify(roe)
            # Fallback to manual calculation
            financials = ticker.financials
            balance_sheet = ticker.balance_sheet
            if financials.empty or balance_sheet.empty:
                return None, "Keine Daten verfügbar"
            net_income = financials.loc['Net Income'].iloc[0]
            equity_current = balance_sheet.loc['Total Stockholder Equity'].iloc[0]
            equity_previous = balance_sheet.loc['Total Stockholder Equity'].iloc[1]
            avg_equity = (equity_current + equity_previous) / 2
            if avg_equity <= 0:
                return None, "Ungültiges Eigenkapital"
            roe = net_income / avg_equity
            roe = float(roe)
            return roe, self.classify(roe)
        except Exception as e:
            return None, f"Fehler bei ROE-Berechnung: {str(e)}"

    def classify(self, roe: float) -> str:
        if roe >= SCHWELLENWERTE['ROE_exzellent']:
            return "Exzellent"
        elif roe >= SCHWELLENWERTE['ROE_min']:
            return "Gut"
        else:
            return "Schwach"