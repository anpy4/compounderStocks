from typing import Tuple, Optional
from src.thresholds import SCHWELLENWERTE
from src.metrics.metrics import (
    MetricCalculator, finite_number, previous_annual_period, statement_value, total_debt,
)

class ROICCalculator(MetricCalculator):
    def calculate(self, ticker) -> Tuple[Optional[float], str]:
        """NOPAT / average cash-adjusted invested capital for the fiscal year.

        Use closing capital if opening capital is unavailable, and a normalized
        25% tax assumption if the effective tax rate is unavailable or abnormal.
        """
        try:
            financials = ticker.financials
            balance_sheet = ticker.balance_sheet
            if financials.empty or balance_sheet.empty:
                return None, "Keine Daten verfügbar"

            period = max(financials.columns)
            if period not in balance_sheet.columns:
                return None, "Keine übereinstimmenden Berichtsperioden"
            operating_income = statement_value(financials, ['Operating Income', 'EBIT'], period)
            pretax_income = statement_value(financials, ['Pretax Income'], period)
            if operating_income is None:
                interest_expense = statement_value(financials, ['Interest Expense'], period)
                interest_income = statement_value(financials, ['Interest Income'], period)
                if pretax_income is not None and interest_expense is not None:
                    interest_income = interest_income if interest_income is not None else 0.0
                    operating_income = pretax_income + interest_expense - interest_income

            # Reconstruct only when the full operating cost base is known.
            if operating_income is None:
                gross_profit = statement_value(financials, ['Gross Profit'], period)
                operating_expenses = statement_value(financials, ['Operating Expense'], period)
                if gross_profit is None:
                    revenue = statement_value(financials, ['Total Revenue', 'Operating Revenue'], period)
                    cost_of_revenue = statement_value(financials, ['Cost Of Revenue'], period)
                    if revenue is not None and cost_of_revenue is not None:
                        gross_profit = revenue - cost_of_revenue
                if gross_profit is not None and operating_expenses is not None:
                    operating_income = gross_profit - operating_expenses
            operating_income = finite_number(operating_income)
            if operating_income is None:
                return None, "Operating Income nicht berechenbar"

            tax_rate = 0.25
            tax_provision = statement_value(financials, ['Tax Provision'], period)
            if pretax_income is not None and pretax_income > 0 and tax_provision is not None:
                effective_rate = tax_provision / pretax_income
                if 0 <= effective_rate <= 1:
                    tax_rate = effective_rate
            nopat = operating_income * (1 - tax_rate)

            invested_capital = self._get_invested_capital(balance_sheet, period)
            if invested_capital is None or invested_capital <= 0:
                return None, "Ungültiges Invested Capital"
            previous = previous_annual_period(balance_sheet, period)
            if previous is not None:
                opening_capital = self._get_invested_capital(balance_sheet, previous)
                if opening_capital is None or opening_capital <= 0:
                    return None, "Ungültiges Anfangskapital"
                invested_capital = invested_capital / 2 + opening_capital / 2

            roic = finite_number(nopat / invested_capital)
            if roic is None:
                return None, "ROIC nicht berechenbar"
            return roic, self.classify(roic)
        except Exception as e:
            return None, f"Fehler bei ROIC-Berechnung: {str(e)}"

    def classify(self, value: float) -> str:
        if value >= SCHWELLENWERTE['ROIC_exzellent']:
            return "Exzellent"
        elif value >= SCHWELLENWERTE['ROIC_min']:
            return "Gut"
        else:
            return "Schwach"

    def _get_invested_capital(self, bs_df, period=None):
        """Yahoo gross invested capital (equity + debt), less cash, consistently.

        Total capitalization may omit current debt; assets omit the deduction
        of non-interest-bearing liabilities. Neither is an equivalent fallback.
        Undisclosed cash is conservatively not deducted.
        """
        if bs_df.empty:
            return None
        if period is None:
            period = max(bs_df.columns)
        capital = statement_value(bs_df, ['Invested Capital'], period)
        if capital is None:
            equity = statement_value(bs_df, [
                'Total Equity Gross Minority Interest', 'Total Stockholder Equity',
                'Stockholders Equity', 'Common Stock Equity',
            ], period)
            debt = total_debt(bs_df, period)
            if equity is None or debt is None:
                return None
            capital = equity + debt
        cash = statement_value(bs_df, [
            'Cash And Cash Equivalents', 'Cash Cash Equivalents And Short Term Investments',
            'Cash Equivalents',
        ], period)
        if cash is None:
            cash = 0.0
        if cash < 0:
            return None
        return finite_number(capital - cash)
