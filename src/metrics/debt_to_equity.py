from typing import Tuple, Optional
from src.thresholds import SCHWELLENWERTE
from src.metrics.metrics import MetricCalculator, finite_number, statement_value, total_debt

class DebtToEquityCalculator(MetricCalculator):
    def calculate(self, ticker) -> Tuple[Optional[float], str]:
        """Interest-bearing debt / shareholders' equity at the latest year end."""
        try:
            balance_sheet = ticker.balance_sheet
            if balance_sheet.empty:
                return None, "Keine Bilanzdaten verfügbar"

            period = max(balance_sheet.columns)
            equity = statement_value(balance_sheet, [
                'Total Stockholder Equity', 'Stockholders Equity', 'Common Stock Equity',
            ], period)
            if equity is None or equity <= 0:
                return None, "Ungültiges Eigenkapital"

            debt = total_debt(balance_sheet, period)
            if debt is None:
                return None, "Gesamtverschuldung nicht verfügbar oder ungültig"

            debt_to_equity = finite_number(debt / equity)
            if debt_to_equity is None:
                return None, "Debt-to-Equity nicht berechenbar"
            return debt_to_equity, self.classify(debt_to_equity)
        except Exception as e:
            return None, f"Fehler bei Debt-to-Equity-Berechnung: {str(e)}"

    def classify(self, value: float) -> str:
        if value <= SCHWELLENWERTE['Debt_Equity_konservativ']:
            return "Sehr konservativ"
        elif value <= SCHWELLENWERTE['Debt_Equity_max']:
            return "Konservativ"
        else:
            return "Hoch verschuldet"