from typing import Tuple, Optional
from src.thresholds import SCHWELLENWERTE
from src.metrics.metrics import MetricCalculator

class FCFMarginCalculator(MetricCalculator):
    def calculate(self, ticker) -> Tuple[Optional[float], str]:
        # Implementation of FCF Margin calculation
        try:
            cashflow = ticker.cashflow
            financials = ticker.financials
            if cashflow.empty or financials.empty:
                return None, "Keine Daten verfügbar"

            # Free Cash Flow
            if 'Free Cash Flow' in cashflow.index:
                fcf = cashflow.loc['Free Cash Flow'].iloc[0]
            elif 'Operating Cash Flow' in cashflow.index and 'Capital Expenditure' in cashflow.index:
                ocf = cashflow.loc['Operating Cash Flow'].iloc[0]
                capex = abs(cashflow.loc['Capital Expenditure'].iloc[0])  # CapEx is usually negative
                fcf = ocf - capex
            else:
                return None, "Free Cash Flow nicht berechenbar"

            # Revenue
            revenue = None
            for key in ['Total Revenue', 'Revenue']:
                if key in financials.index:
                    revenue = financials.loc[key].iloc[0]
                    if revenue != 0:
                        break

            if revenue is None or revenue == 0:
                return None, "Umsatz ist Null oder nicht verfügbar"

            # FCF-Margin mit absoluten Werten
            fcf_margin = fcf / abs(revenue) if revenue != 0 else None

            if fcf_margin is None:
                return None, "FCF-Margin nicht berechenbar"

            return float(fcf_margin), self.classify(fcf_margin)
        except Exception as e:
            return None, f"Fehler bei FCF-Margin-Berechnung: {str(e)}"

    def classify(self, fcf_margin: float) -> str:
        if fcf_margin >= SCHWELLENWERTE['FCF_Marge_stark']:
            return "Stark"
        elif fcf_margin >= SCHWELLENWERTE['FCF_Marge_min']:
            return "Gut"
        else:
            return "Schwach"