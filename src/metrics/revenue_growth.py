from typing import Tuple, Optional
from src.thresholds import SCHWELLENWERTE
from src.metrics.metrics import MetricCalculator, average_annual_growth

class RevenueGrowthCalculator(MetricCalculator):
    def calculate(self, ticker) -> Tuple[Optional[float], str]:
        """Arithmetic mean of historical annual revenue growth, not CAGR."""
        try:
            financials = ticker.financials

            if financials.empty or len(financials.columns) < 2:
                return None, "Nicht genügend historische Daten"

            for label in ['Total Revenue', 'Revenue']:
                if label in financials.index:
                    growth = average_annual_growth(financials.loc[label])
                    if growth is not None:
                        return growth, self.classify(growth)
            return None, "Umsatzwachstum aus gültigen Jahresperioden nicht berechenbar"

        except Exception as e:
            return None, f"Fehler bei Umsatzwachstum-Berechnung: {str(e)}"

    def classify(self, value: float) -> str:
        if value >= SCHWELLENWERTE['Umsatzwachstum_stark']:
            return "Stark"
        elif value >= SCHWELLENWERTE['Umsatzwachstum_min']:
            return "Gut"
        else:
            return "Schwach"
