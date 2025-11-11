from typing import Tuple, Optional
from src.thresholds import SCHWELLENWERTE
from src.metrics.metrics import MetricCalculator
import pandas as pd

class DebtToEquityCalculator(MetricCalculator):
    def calculate(self, ticker) -> Tuple[Optional[float], str]:
        # Implementation of Debt-to-Equity calculation
        try:
            balance_sheet = ticker.balance_sheet
            if balance_sheet.empty:
                return None, "Keine Bilanzdaten verfügbar"

            # Eigenkapital
            if 'Total Stockholder Equity' in balance_sheet.index:
                equity = balance_sheet.loc['Total Stockholder Equity'].iloc[0]
            elif 'Stockholders Equity' in balance_sheet.index:
                equity = balance_sheet.loc['Stockholders Equity'].iloc[0]
            else:
                return None, "Eigenkapital nicht gefunden"

            if equity <= 0:
                return None, "Ungültiges Eigenkapital"

            # Gesamtverschuldung
            total_debt = 0
            debt_items = ['Long Term Debt', 'Short Long Term Debt', 'Current Debt', 'Total Debt']
            for item in debt_items:
                if item in balance_sheet.index:
                    debt_value = balance_sheet.loc[item].iloc[0]
                    if pd.notna(debt_value):
                        total_debt += debt_value

            debt_to_equity = total_debt / equity
            debt_to_equity = float(debt_to_equity)
            return debt_to_equity, self.classify(debt_to_equity)
        except Exception as e:
            return None, f"Fehler bei Debt-to-Equity-Berechnung: {str(e)}"

    def classify(self, ratio: float) -> str:
        if ratio <= SCHWELLENWERTE['Debt_Equity_konservativ']:
            return "Sehr konservativ"
        elif ratio <= SCHWELLENWERTE['Debt_Equity_max']:
            return "Konservativ"
        else:
            return "Hoch verschuldet"