from typing import Tuple, Optional
import pandas as pd
from src.thresholds import SCHWELLENWERTE
from src.metrics.metrics import MetricCalculator, average_annual_growth, statement_value


class EpsGrowthCalculator(MetricCalculator):

    def calculate(self, ticker) -> Tuple[Optional[float], str]:
        """Historical annual EPS growth, preferring diluted over basic EPS.

        Profit growth alone ignores dilution; analyst estimates are not history.
        Reconstruct EPS only with common-shareholder income and average shares.
        """
        try:
            financials = ticker.financials
            if financials.empty or len(financials.columns) < 2:
                return None, "Nicht genügend historische Daten"

            for eps_label, shares_label in [
                ('Diluted EPS', 'Diluted Average Shares'),
                ('Basic EPS', 'Basic Average Shares'),
            ]:
                if eps_label in financials.index:
                    growth = average_annual_growth(financials.loc[eps_label], allow_losses=True)
                    if growth is not None:
                        return growth, self.classify(growth)

                earnings = {}
                for period in financials.columns:
                    income = statement_value(financials, ['Net Income Common Stockholders'], period)
                    shares = statement_value(financials, [shares_label], period)
                    earnings[period] = (
                        income / shares
                        if income is not None and shares is not None and shares > 0
                        else float('nan')
                    )
                growth = average_annual_growth(pd.Series(earnings), allow_losses=True)
                if growth is not None:
                    return growth, self.classify(growth)
            return None, "Historisches EPS-Wachstum nicht berechenbar"

        except Exception as e:
            return None, f"Fehler bei EPS-Wachstum-Berechnung: {str(e)}"

    def classify(self, value: float) -> str:
        if value >= SCHWELLENWERTE['EPS_Wachstum_stark']:
            return "Stark"
        elif value >= SCHWELLENWERTE['EPS_Wachstum_min']:
            return "Gut"
        else:
            return "Schwach"
