from typing import Tuple, Optional
from src.thresholds import SCHWELLENWERTE
from src.metrics.metrics import MetricCalculator, finite_number, statement_value

class FCFMarginCalculator(MetricCalculator):
    def calculate(self, ticker) -> Tuple[Optional[float], str]:
        """Annual free cash flow / positive revenue for the same fiscal year."""
        try:
            cashflow = ticker.cashflow
            financials = ticker.financials
            if cashflow.empty or financials.empty:
                return None, "Keine Daten verfügbar"

            period = max(financials.columns)
            if period not in cashflow.columns:
                return None, "Keine übereinstimmenden Berichtsperioden"
            fcf = statement_value(cashflow, ['Free Cash Flow'], period)
            if fcf is None:
                ocf = statement_value(cashflow, ['Operating Cash Flow'], period)
                capex = statement_value(cashflow, ['Capital Expenditure'], period)
                if ocf is None or capex is None:
                    return None, "Free Cash Flow nicht berechenbar"
                # Providers report investment outflows either signed or unsigned.
                fcf = ocf - abs(capex)

            revenue = statement_value(financials, ['Total Revenue', 'Revenue'], period)
            if revenue is None or revenue <= 0:
                return None, "Umsatz ist nicht positiv oder nicht verfügbar"

            fcf_margin = finite_number(fcf / revenue)
            if fcf_margin is None:
                return None, "FCF-Margin nicht berechenbar"

            return fcf_margin, self.classify(fcf_margin)
        except Exception as e:
            return None, f"Fehler bei FCF-Margin-Berechnung: {str(e)}"

    def classify(self, value: float) -> str:
        if value >= SCHWELLENWERTE['FCF_Marge_stark']:
            return "Stark"
        elif value >= SCHWELLENWERTE['FCF_Marge_min']:
            return "Gut"
        else:
            return "Schwach"