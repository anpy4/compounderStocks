from typing import Tuple, Optional
import pandas as pd
from src.thresholds import SCHWELLENWERTE
from src.metrics.metrics import MetricCalculator

class RevenueGrowthCalculator(MetricCalculator):
    def calculate(self, ticker) -> Tuple[Optional[float], str]:
        """
       Berechnet durchschnittliches Umsatzwachstum über die letzten Jahre
       """
        try:
            financials = ticker.financials

            if financials.empty or len(financials.columns) < 2:
                return None, "Nicht genügend historische Daten"

            # Umsatz für verschiedene Jahre
            if 'Total Revenue' in financials.index:
                revenues = financials.loc['Total Revenue']
            elif 'Revenue' in financials.index:
                revenues = financials.loc['Revenue']
            else:
                return None, "Umsatz nicht gefunden"

            # Berechne Wachstumsraten Jahr-für-Jahr
            growth_rates = []
            for i in range(len(revenues) - 1):
                current = revenues.iloc[i]
                previous = revenues.iloc[i + 1]
                if pd.isna(previous) or previous == 0:
                    continue
                growth = (current - previous) / abs(previous)
                growth_rates.append(growth)

            if not growth_rates:
                return None, "Wachstumsraten nicht berechenbar"

            # Durchschnittliche Wachstumsrate
            avg_growth = sum(growth_rates) / len(growth_rates)
            avg_growth = float(avg_growth)
            bewertung = self.classify(avg_growth)

            return avg_growth, bewertung

        except Exception as e:
            return None, f"Fehler bei Umsatzwachstum-Berechnung: {str(e)}"

    def classify(self, growth: float) -> str:
        if growth >= SCHWELLENWERTE['Umsatzwachstum_stark']:
            return "Stark"
        elif growth >= SCHWELLENWERTE['Umsatzwachstum_min']:
            return "Gut"
        else:
            return "Schwach"
