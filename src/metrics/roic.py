from typing import Tuple, Optional
from src.thresholds import SCHWELLENWERTE
from src.metrics.metrics import MetricCalculator

class ROICCalculator(MetricCalculator):
    def calculate(self, ticker) -> Tuple[Optional[float], str]:
        """
            Berechnet Return on Invested Capital (ROIC) = NOPAT / Invested Capital
            NOPAT = Operating Income * (1 - Tax Rate)
            Invested Capital = Total Equity + Total Debt - Cash
            """
        try:
            # Versuche aus info (falls verfügbar)
            if hasattr(ticker, 'info') and 'returnOnAssets' in ticker.info:
                # ROA ist nicht ROIC, aber eine Approximation wenn ROIC nicht verfügbar
                pass

            financials = ticker.financials
            balance_sheet = ticker.balance_sheet

            if financials.empty or balance_sheet.empty:
                return None, "Keine Daten verfügbar"

            # Operating Income (EBIT) mit Fallback
            operating_income = None

            # 1. Direkter Zugriff
            if 'Operating Income' in financials.index:
                operating_income = financials.loc['Operating Income'].iloc[0]
            elif 'EBIT' in financials.index:
                operating_income = financials.loc['EBIT'].iloc[0]

            # 2. Von Pretax Income hochrechnen (EMPFOHLEN)
            if operating_income is None:
                try:
                    pretax_income = financials.loc['Pretax Income'].iloc[0]
                    interest_expense = financials.loc['Interest Expense'].iloc[
                        0] if 'Interest Expense' in financials.index else 0
                    interest_income = financials.loc['Interest Income'].iloc[
                        0] if 'Interest Income' in financials.index else 0
                    operating_income = pretax_income + interest_expense - interest_income
                except:
                    pass

            # 3. Aus Revenue und Betriebsausgaben (Top-Down)
            if operating_income is None:
                try:
                    total_revenue = financials.loc['Total Revenue'].iloc[0] if 'Total Revenue' in financials.index else \
                    financials.loc['Operating Revenue'].iloc[0]
                    sga = financials.loc['Selling General And Administration'].iloc[0]
                    other_expenses = financials.loc['Professional Expense And Contract Services Expense'].iloc[0]
                    operating_income = total_revenue - sga - other_expenses
                except:
                    pass

            # 4. Normalized Income als Fallback
            if operating_income is None and 'Normalized Income' in financials.index:
                operating_income = financials.loc['Normalized Income'].iloc[0]

            if operating_income is None:
                return None, "Operating Income nicht berechenbar"

            # Tax Rate schätzen
            if 'Tax Provision' in financials.index and 'Pretax Income' in financials.index:
                tax_provision = financials.loc['Tax Provision'].iloc[0]
                pretax_income = financials.loc['Pretax Income'].iloc[0]
                tax_rate = abs(tax_provision) / pretax_income if pretax_income != 0 else 0.25  # Standard 25%
            else:
                tax_rate = 0.25  # Standard Steuersatz

            # NOPAT berechnen
            nopat = operating_income * (1 - tax_rate)

            # Invested Capital berechnen
            invested_capital = self._get_invested_capital(balance_sheet)

            if invested_capital <= 0:
                return None, "Ungültiges Invested Capital"

            roic = nopat / invested_capital
            roic = float(roic)
            bewertung = self.classify(roic)

            return roic, bewertung

        except Exception as e:
            return None, f"Fehler bei ROIC-Berechnung: {str(e)}"

    def classify(self, roic: float) -> str:
        if roic >= SCHWELLENWERTE['ROIC_exzellent']:
            return "Exzellent"
        elif roic >= SCHWELLENWERTE['ROIC_min']:
            return "Gut"
        else:
            return "Schwach"

    def _get_invested_capital(self, bs_df):
        # 1. Direkt
        if "Invested Capital" in bs_df.index:
            return bs_df.loc["Invested Capital"].iloc[0]

        # 2. Total Equity + Total Debt - Cash
        # Equity
        equity_candidates = ["Total Equity Gross Minority Interest", "Stockholders Equity", "Common Stock Equity"]
        equity = next((bs_df.loc[label].iloc[0] for label in equity_candidates if label in bs_df.index), None)
        # Debt
        debt_candidates = ["Total Debt"]
        debt = next((bs_df.loc[label].iloc[0] for label in debt_candidates if label in bs_df.index), None)
        # Fallback Debt: Long Term Debt + Current Debt
        if debt is None:
            long_debt = bs_df.loc["Long Term Debt"].iloc[0] if "Long Term Debt" in bs_df.index else 0
            current_debt = bs_df.loc["Current Debt"].iloc[0] if "Current Debt" in bs_df.index else 0
            debt = long_debt + current_debt
        # Cash
        cash_candidates = ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments",
                           "Cash Equivalents"]
        cash = next((bs_df.loc[label].iloc[0] for label in cash_candidates if label in bs_df.index), 0)
        if equity is not None and debt is not None:
            return equity + debt - cash

        # 3. Total Capitalization
        if "Total Capitalization" in bs_df.index:
            return bs_df.loc["Total Capitalization"].iloc[0]

        # 4. Assets - Cash
        if "Total Assets" in bs_df.index:
            cash = bs_df.loc["Cash And Cash Equivalents"].iloc[
                0] if "Cash And Cash Equivalents" in bs_df.index else 0
            return bs_df.loc["Total Assets"].iloc[0] - cash

        # Fallback: None found
        return None