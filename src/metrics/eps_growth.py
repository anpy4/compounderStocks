from typing import Tuple, Optional
from src.thresholds import SCHWELLENWERTE
from src.metrics.metrics import MetricCalculator


class EpsGrowthCalculator(MetricCalculator):

    def calculate(self, ticker) -> Tuple[Optional[float], str]:
        """
        Berechnet EPS-Wachstum. Falls EPS nicht verfügbar, nutze Nettogewinn-Wachstum
        """
        try:
            # Versuche EPS aus info
            if hasattr(ticker, 'info'):
                eps_current = ticker.info.get('trailingEps')
                eps_forward = ticker.info.get('forwardEps')
                if eps_current and eps_forward:
                    growth = (eps_forward - eps_current) / abs(eps_current)
                    bewertung = self.classify(growth)
                    return growth, bewertung

            # Falls nicht verfügbar, berechne aus Nettogewinn
            financials = ticker.financials

            if financials.empty or len(financials.columns) < 2:
                return None, "Nicht genügend historische Daten"

            # Nettogewinn für verschiedene Jahre
            if 'Net Income' in financials.index:
                earnings = financials.loc['Net Income']
            elif 'Net Income Common Stockholders' in financials.index:
                earnings = financials.loc['Net Income Common Stockholders']
            else:
                return None, "Nettogewinn nicht gefunden"

            # Berechne Wachstumsraten
            growth_rates = []
            for i in range(len(earnings) - 1):
                current = earnings.iloc[i]
                previous = earnings.iloc[i + 1]
                if previous != 0:
                    growth = (current - previous) / abs(previous)
                    growth_rates.append(growth)

            if not growth_rates:
                return None, "Wachstumsraten nicht berechenbar"

            avg_growth = sum(growth_rates) / len(growth_rates)
            avg_growth = float(avg_growth)
            bewertung = self.classify(avg_growth)

            return avg_growth, bewertung

        except Exception as e:
            return None, f"Fehler bei EPS-Wachstum-Berechnung: {str(e)}"

    def classify(self, growth: float) -> str:
        if growth >= SCHWELLENWERTE['EPS_Wachstum_stark']:
            return "Stark"
        elif growth >= SCHWELLENWERTE['EPS_Wachstum_min']:
            return "Gut"
        else:
            return "Schwach"
