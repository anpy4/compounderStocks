"""Offline financial examples: amounts are arbitrary, ratios are decimal fractions."""

from types import SimpleNamespace

import pandas as pd
import pytest

from src.metrics.debt_to_equity import DebtToEquityCalculator
from src.metrics.eps_growth import EpsGrowthCalculator
from src.metrics.fcf import FCFMarginCalculator
from src.metrics.revenue_growth import RevenueGrowthCalculator
from src.metrics.roe import ROECalculator
from src.metrics.roic import ROICCalculator
from src.thresholds import SCHWELLENWERTE


def statement(rows, years=(2024, 2023, 2022, 2021)):
    """Match yfinance: line items in rows, fiscal year ends in columns."""
    count = len(next(iter(rows.values()))) if rows else 0
    dates = pd.to_datetime([f"{year}-12-31" for year in years[:count]])
    return pd.DataFrame.from_dict(rows, orient="index", columns=dates)


def ticker(*, financials=None, balance_sheet=None, cashflow=None, info=None):
    return SimpleNamespace(
        ticker="TEST",
        financials=statement(financials or {}),
        balance_sheet=statement(balance_sheet or {}),
        cashflow=statement(cashflow or {}),
        info=info or {},
    )


def assert_metric(calculator, company, expected, rating=None):
    value, actual_rating = calculator.calculate(company)
    assert value == pytest.approx(expected)
    assert isinstance(value, float)
    if rating is not None:
        assert actual_rating == rating


def assert_unavailable(calculator, company):
    value, reason = calculator.calculate(company)
    assert value is None
    assert isinstance(reason, str) and reason


CALCULATORS = [
    ROECalculator,
    ROICCalculator,
    FCFMarginCalculator,
    RevenueGrowthCalculator,
    EpsGrowthCalculator,
    DebtToEquityCalculator,
]


@pytest.mark.parametrize("calculator_type", CALCULATORS)
def test_empty_statements_are_unavailable(calculator_type):
    assert_unavailable(calculator_type(), ticker())


@pytest.mark.parametrize("calculator_type", CALCULATORS)
def test_data_access_failure_returns_reason(calculator_type):
    class UnavailableTicker:
        info = {}

        def __getattr__(self, name):
            raise RuntimeError("Data provider unavailable")

    assert_unavailable(calculator_type(), UnavailableTicker())


@pytest.mark.parametrize("calculator_type", CALCULATORS)
@pytest.mark.parametrize("invalid", [float("nan"), float("inf")])
def test_nonfinite_statements_never_produce_a_metric(calculator_type, invalid):
    company = ticker(
        financials={label: [invalid, invalid] for label in [
            "Net Income", "Operating Income", "Pretax Income", "Tax Provision",
            "Total Revenue", "Diluted EPS",
        ]},
        balance_sheet={label: [invalid, invalid] for label in [
            "Stockholders Equity", "Total Debt", "Cash And Cash Equivalents",
        ]},
        cashflow={"Free Cash Flow": [invalid, invalid]},
    )
    assert_unavailable(calculator_type(), company)


@pytest.mark.parametrize("calculator, expected", [
    (ROECalculator, 0.18), (ROICCalculator, 16 / 130),
    (FCFMarginCalculator, 0.15), (DebtToEquityCalculator, 50 / 120),
])
@pytest.mark.parametrize("order", [[2, 1, 0], [1, 0, 2]])
def test_latest_year_and_opening_capital_are_independent_of_column_order(calculator, expected, order):
    company = ticker(
        financials={
            "Net Income": [18, 16, 14], "Operating Income": [20, 18, 16],
            "Pretax Income": [20, 18, 16], "Tax Provision": [4, 3.6, 3.2],
            "Total Revenue": [200, 180, 160],
        },
        balance_sheet={"Stockholders Equity": [120, 80, 60],
                       "Total Debt": [50, 40, 30], "Cash And Cash Equivalents": [20, 10, 5]},
        cashflow={"Free Cash Flow": [30, 20, 10]},
    )
    for attribute in ["financials", "balance_sheet", "cashflow"]:
        setattr(company, attribute, getattr(company, attribute).iloc[:, order])
    assert_metric(calculator(), company, expected)


@pytest.mark.parametrize("equity_label", [
    "Total Stockholder Equity", "Stockholders Equity", "Common Stock Equity",
])
def test_roe_uses_average_opening_and_closing_equity(equity_label):
    company = ticker(
        financials={"Net Income": [18]},
        balance_sheet={equity_label: [120, 80]},
    )
    assert_metric(ROECalculator(), company, 0.18, "Exzellent")


@pytest.mark.parametrize("value", [0.0, -0.1, 0.18])
def test_roe_provider_value_is_already_a_decimal_fraction(value):
    assert_metric(ROECalculator(), ticker(info={"returnOnEquity": value}), value)


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), "invalid"])
def test_roe_invalid_provider_value_uses_manual_fallback(value):
    company = ticker(
        info={"returnOnEquity": value}, financials={"Net Income": [15]},
        balance_sheet={"Stockholders Equity": [120, 80]},
    )
    assert_metric(ROECalculator(), company, 0.15, "Gut")


def test_roe_info_failure_does_not_prevent_statement_fallback():
    class Company:
        financials = statement({"Net Income": [15]})
        balance_sheet = statement({"Stockholders Equity": [120, 80]})

        @property
        def info(self):
            raise RuntimeError("Info endpoint unavailable")

    assert_metric(ROECalculator(), Company(), 0.15)


@pytest.mark.parametrize("equity", [[100], [0, 100], [-10, 100], [100, -10], [float("nan"), 100]])
def test_roe_requires_two_valid_positive_equity_observations(equity):
    assert_unavailable(ROECalculator(), ticker(
        financials={"Net Income": [10]}, balance_sheet={"Stockholders Equity": equity},
    ))


def test_roe_requires_matching_fiscal_periods():
    company = ticker(financials={"Net Income": [10]}, balance_sheet={"Stockholders Equity": [100, 90]})
    company.balance_sheet.columns = pd.to_datetime(["2023-12-31", "2022-12-31"])
    assert_unavailable(ROECalculator(), company)


def test_roe_does_not_mix_common_equity_with_minority_income():
    company = ticker(financials={"Net Income": [10]}, balance_sheet={"Total Equity Gross Minority Interest": [100, 90]})
    assert_unavailable(ROECalculator(), company)


def test_roe_preserves_net_losses():
    assert_metric(ROECalculator(), ticker(
        financials={"Net Income": [-18]}, balance_sheet={"Stockholders Equity": [120, 80]},
    ), -0.18, "Schwach")


def test_debt_to_equity_does_not_count_components_twice():
    company = ticker(balance_sheet={
        "Stockholders Equity": [100], "Total Debt": [60], "Long Term Debt": [40],
        "Current Debt": [20], "Short Long Term Debt": [10],
    })
    assert_metric(DebtToEquityCalculator(), company, 0.6, "Konservativ")


@pytest.mark.parametrize("current_label", ["Current Debt", "Short Term Debt", "Short Long Term Debt"])
def test_debt_to_equity_component_fallback(current_label):
    company = ticker(balance_sheet={
        "Stockholders Equity": [100], "Long Term Debt": [40], current_label: [10],
    })
    assert_metric(DebtToEquityCalculator(), company, 0.5, "Sehr konservativ")


def test_debt_to_equity_uses_current_debt_before_overlapping_alias():
    company = ticker(balance_sheet={
        "Stockholders Equity": [100], "Long Term Debt": [40], "Current Debt": [20],
        "Short Long Term Debt": [10],
    })
    assert_metric(DebtToEquityCalculator(), company, 0.6)


def test_explicit_zero_debt_is_not_missing_debt():
    assert_metric(DebtToEquityCalculator(), ticker(balance_sheet={
        "Stockholders Equity": [100], "Total Debt": [0], "Long Term Debt": [40],
    }), 0.0, "Sehr konservativ")


@pytest.mark.parametrize("debt_rows", [{}, {"Long Term Debt": [40]}, {"Total Debt": [-10]}, {"Total Debt": [float("nan")]}])
def test_missing_or_invalid_debt_is_not_assumed_to_be_zero(debt_rows):
    assert_unavailable(DebtToEquityCalculator(), ticker(balance_sheet={"Stockholders Equity": [100], **debt_rows}))


@pytest.mark.parametrize("equity", [0, -1, float("nan"), float("inf")])
def test_debt_to_equity_rejects_invalid_equity(equity):
    assert_unavailable(DebtToEquityCalculator(), ticker(balance_sheet={"Stockholders Equity": [equity], "Total Debt": [20]}))


@pytest.mark.parametrize("capex", [-30, 30])
def test_fcf_margin_capex_sign_conventions(capex):
    assert_metric(FCFMarginCalculator(), ticker(
        financials={"Total Revenue": [500]},
        cashflow={"Operating Cash Flow": [100], "Capital Expenditure": [capex]},
    ), 0.14, "Stark")


@pytest.mark.parametrize("fcf, expected", [(0, 0.0), (-20, -0.04), (50, 0.10)])
def test_fcf_margin_preserves_cashflow_sign_and_prefers_reported_fcf(fcf, expected):
    assert_metric(FCFMarginCalculator(), ticker(
        financials={"Revenue": [500]},
        cashflow={"Free Cash Flow": [fcf], "Operating Cash Flow": [100], "Capital Expenditure": [-30]},
    ), expected)


def test_fcf_nan_reported_value_uses_ocf_minus_capex():
    assert_metric(FCFMarginCalculator(), ticker(
        financials={"Total Revenue": [500]}, cashflow={
            "Free Cash Flow": [float("nan")], "Operating Cash Flow": [100], "Capital Expenditure": [-30],
        },
    ), 0.14)


def test_fcf_fallback_preserves_negative_operating_cashflow():
    assert_metric(FCFMarginCalculator(), ticker(
        financials={"Total Revenue": [500]},
        cashflow={"Operating Cash Flow": [-60], "Capital Expenditure": [-20]},
    ), -0.16, "Schwach")


@pytest.mark.parametrize("revenue", [0, -500, float("nan"), float("inf")])
def test_fcf_margin_requires_positive_finite_revenue(revenue):
    assert_unavailable(FCFMarginCalculator(), ticker(financials={"Total Revenue": [revenue]}, cashflow={"Free Cash Flow": [50]}))


def test_fcf_margin_rejects_mismatched_years():
    company = ticker(financials={"Total Revenue": [500]}, cashflow={"Free Cash Flow": [50]})
    company.cashflow.columns = pd.to_datetime(["2023-12-31"])
    assert_unavailable(FCFMarginCalculator(), company)


@pytest.mark.parametrize("row, calculator", [("Total Revenue", RevenueGrowthCalculator), ("Diluted EPS", EpsGrowthCalculator)])
def test_growth_is_arithmetic_mean_of_year_on_year_rates_not_cagr(row, calculator):
    # +50% followed by -20%: arithmetic mean 15%, CAGR sqrt(1.2)-1 ~= 9.54%.
    assert_metric(calculator(), ticker(financials={row: [120, 150, 100]}), 0.15, "Stark")


@pytest.mark.parametrize("row, calculator", [("Total Revenue", RevenueGrowthCalculator), ("Diluted EPS", EpsGrowthCalculator)])
@pytest.mark.parametrize("order", [[0, 1, 2], [2, 1, 0], [1, 0, 2]])
def test_growth_orders_periods_by_date(row, calculator, order):
    company = ticker(financials={row: [121, 110, 100]})
    company.financials = company.financials.iloc[:, order]
    assert_metric(calculator(), company, 0.1)


@pytest.mark.parametrize("row, calculator", [("Total Revenue", RevenueGrowthCalculator), ("Diluted EPS", EpsGrowthCalculator)])
@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), None])
def test_growth_skips_invalid_pairs_without_bridging_missing_year(row, calculator, invalid):
    assert_metric(calculator(), ticker(financials={row: [121, invalid, 100, 80]}), 0.25)


@pytest.mark.parametrize("row, calculator", [("Total Revenue", RevenueGrowthCalculator), ("Diluted EPS", EpsGrowthCalculator)])
def test_growth_does_not_call_multiyear_change_annual_growth(row, calculator):
    company = ticker(financials={row: [121, 100]})
    company.financials.columns = pd.to_datetime(["2024-12-31", "2022-12-31"])
    assert_unavailable(calculator(), company)


@pytest.mark.parametrize("row, calculator", [("Total Revenue", RevenueGrowthCalculator), ("Diluted EPS", EpsGrowthCalculator)])
def test_growth_accepts_52_and_53_week_fiscal_years(row, calculator):
    company = ticker(financials={row: [121, 110, 100]})
    company.financials.columns = pd.to_datetime(["2024-12-28", "2023-12-30", "2022-12-24"])
    assert_metric(calculator(), company, 0.1)


@pytest.mark.parametrize("row, calculator", [("Total Revenue", RevenueGrowthCalculator), ("Diluted EPS", EpsGrowthCalculator)])
def test_quarterly_change_is_not_reported_as_annual_growth(row, calculator):
    company = ticker(financials={row: [110, 100]})
    company.financials.columns = pd.to_datetime(["2024-12-31", "2024-09-30"])
    assert_unavailable(calculator(), company)


@pytest.mark.parametrize("row, calculator", [("Total Revenue", RevenueGrowthCalculator), ("Diluted EPS", EpsGrowthCalculator)])
@pytest.mark.parametrize("values", [[100], [100, 0], [100, -50], [float("nan"), 100]])
def test_growth_requires_a_valid_positive_base(row, calculator, values):
    assert_unavailable(calculator(), ticker(financials={row: values}))


def test_revenue_growth_accepts_zero_current_revenue():
    assert_metric(RevenueGrowthCalculator(), ticker(financials={"Revenue": [0, 100]}), -1.0, "Schwach")


def test_revenue_growth_rejects_negative_current_revenue():
    assert_unavailable(RevenueGrowthCalculator(), ticker(financials={"Total Revenue": [-10, 100]}))


def test_eps_growth_prefers_historical_diluted_eps_over_basic_and_forecasts():
    company = ticker(
        financials={"Diluted EPS": [2.2, 2.0], "Basic EPS": [3.0, 2.0]},
        info={"trailingEps": 2.0, "forwardEps": 4.0},
    )
    assert_metric(EpsGrowthCalculator(), company, 0.1, "Gut")


def test_eps_growth_uses_basic_eps_when_diluted_eps_is_absent():
    assert_metric(EpsGrowthCalculator(), ticker(financials={"Basic EPS": [2.4, 2.0]}), 0.2)


def test_eps_growth_accounts_for_dilution_when_reconstructing_eps():
    company = ticker(financials={
        "Net Income Common Stockholders": [120, 100],
        "Diluted Average Shares": [60, 50],
    })
    # Profit +20%, shares +20% => EPS unchanged, not +20%.
    assert_metric(EpsGrowthCalculator(), company, 0.0, "Schwach")


def test_eps_can_be_reconstructed_from_basic_average_shares():
    assert_metric(EpsGrowthCalculator(), ticker(financials={
        "Net Income Common Stockholders": [120, 100], "Basic Average Shares": [60, 50],
    }), 0.0)


@pytest.mark.parametrize("shares", [0, -10, float("nan"), float("inf")])
def test_reconstructed_eps_requires_positive_finite_shares(shares):
    assert_unavailable(EpsGrowthCalculator(), ticker(financials={
        "Net Income Common Stockholders": [120, 100], "Diluted Average Shares": [shares, 50],
    }))


def test_net_income_growth_alone_is_not_eps_growth():
    assert_unavailable(EpsGrowthCalculator(), ticker(financials={"Net Income": [120, 100]}))


def test_forward_estimate_alone_is_not_historical_eps_growth():
    assert_unavailable(EpsGrowthCalculator(), ticker(info={"trailingEps": 2, "forwardEps": 4}))


def test_eps_decline_into_loss_is_measurable_from_positive_base():
    assert_metric(EpsGrowthCalculator(), ticker(financials={"Diluted EPS": [-1, 2]}), -1.5, "Schwach")


def roic_company(*, financials=None, balance_sheet=None):
    return ticker(
        financials={"Operating Income": [20], "Pretax Income": [20], "Tax Provision": [4]} if financials is None else financials,
        balance_sheet={"Stockholders Equity": [100], "Total Debt": [50], "Cash And Cash Equivalents": [25]} if balance_sheet is None else balance_sheet,
    )


def test_roic_is_after_tax_operating_profit_over_cash_adjusted_capital():
    # NOPAT = 20 * (1-4/20) = 16; capital = 100+50-25 = 125.
    assert_metric(ROICCalculator(), roic_company(), 16 / 125)


def test_roic_averages_opening_and_closing_capital():
    company = roic_company(balance_sheet={"Stockholders Equity": [100, 80], "Total Debt": [50, 40], "Cash And Cash Equivalents": [25, 15]})
    assert_metric(ROICCalculator(), company, 16 / 115)


def test_roic_reported_invested_capital_is_adjusted_for_cash():
    assert_metric(ROICCalculator(), roic_company(balance_sheet={"Invested Capital": [150], "Cash And Cash Equivalents": [25]}), 16 / 125)


def test_roic_missing_cash_is_conservatively_not_deducted():
    assert_metric(ROICCalculator(), roic_company(balance_sheet={"Invested Capital": [150]}), 16 / 150)


def test_roic_does_not_silently_ignore_invalid_opening_capital():
    assert_unavailable(ROICCalculator(), roic_company(balance_sheet={"Invested Capital": [150, -10]}))


def test_roic_component_debt_and_reported_debt_have_the_same_meaning():
    assert_metric(ROICCalculator(), roic_company(balance_sheet={
        "Stockholders Equity": [100], "Long Term Debt": [40], "Current Debt": [10],
        "Short Long Term Debt": [5], "Cash And Cash Equivalents": [25],
    }), 16 / 125)


def test_roic_nan_operating_income_falls_back_to_ebit():
    assert_metric(ROICCalculator(), roic_company(financials={"Operating Income": [float("nan")], "EBIT": [20]}), 15 / 125)


def test_roic_reconstructs_ebit_without_net_interest_income():
    company = roic_company(financials={"Pretax Income": [18], "Interest Expense": [4], "Interest Income": [2], "Tax Provision": [3.6]})
    assert_metric(ROICCalculator(), company, 16 / 125)


def test_roic_reconstructs_operating_income_only_from_complete_operating_costs():
    company = roic_company(financials={"Total Revenue": [100], "Cost Of Revenue": [50], "Operating Expense": [30]})
    assert_metric(ROICCalculator(), company, 15 / 125)


@pytest.mark.parametrize("rows", [
    {"Total Revenue": [100], "Selling General And Administration": [20], "Professional Expense And Contract Services Expense": [10]},
    {"Normalized Income": [20]},
])
def test_roic_does_not_mislabel_partial_margin_or_net_income_as_ebit(rows):
    assert_unavailable(ROICCalculator(), roic_company(financials=rows))


@pytest.mark.parametrize("pretax, tax", [(0, 5), (-20, 5), (20, -5), (20, 25), (20, float("nan"))])
def test_roic_invalid_effective_tax_rate_uses_documented_25_percent_assumption(pretax, tax):
    assert_metric(ROICCalculator(), roic_company(financials={"Operating Income": [20], "Pretax Income": [pretax], "Tax Provision": [tax]}), 15 / 125)


@pytest.mark.parametrize("tax, expected", [(0, 20 / 125), (20, 0)])
def test_roic_accepts_zero_and_full_tax_rates(tax, expected):
    assert_metric(ROICCalculator(), roic_company(financials={"Operating Income": [20], "Pretax Income": [20], "Tax Provision": [tax]}), expected)


@pytest.mark.parametrize("balance_sheet", [
    {"Total Assets": [150], "Cash And Cash Equivalents": [25]},
    {"Total Capitalization": [150]},
    {"Stockholders Equity": [100], "Cash And Cash Equivalents": [25]},
    {"Invested Capital": [0]},
    {"Invested Capital": [-10]},
    {"Invested Capital": [float("nan")]},
])
def test_roic_requires_identifiable_positive_invested_capital(balance_sheet):
    assert_unavailable(ROICCalculator(), roic_company(balance_sheet=balance_sheet))


def test_roic_preserves_operating_losses():
    assert_metric(ROICCalculator(), roic_company(financials={"Operating Income": [-20]}), -15 / 125, "Schwach")


def test_roic_requires_matching_statement_dates():
    company = roic_company()
    company.balance_sheet.columns = pd.to_datetime(["2023-12-31"])
    assert_unavailable(ROICCalculator(), company)


@pytest.mark.parametrize("calculator, minimum_key, strong_key, low, middle, high", [
    (ROECalculator, "ROE_min", "ROE_exzellent", "Schwach", "Gut", "Exzellent"),
    (ROICCalculator, "ROIC_min", "ROIC_exzellent", "Schwach", "Gut", "Exzellent"),
    (FCFMarginCalculator, "FCF_Marge_min", "FCF_Marge_stark", "Schwach", "Gut", "Stark"),
    (RevenueGrowthCalculator, "Umsatzwachstum_min", "Umsatzwachstum_stark", "Schwach", "Gut", "Stark"),
    (EpsGrowthCalculator, "EPS_Wachstum_min", "EPS_Wachstum_stark", "Schwach", "Gut", "Stark"),
])
def test_classification_boundaries_are_inclusive_and_ordered(calculator, minimum_key, strong_key, low, middle, high):
    minimum, strong = SCHWELLENWERTE[minimum_key], SCHWELLENWERTE[strong_key]
    assert minimum < strong
    metric = calculator()
    assert metric.classify(minimum - 1e-9) == low
    assert metric.classify(minimum) == middle
    assert metric.classify(strong - 1e-9) == middle
    assert metric.classify(strong) == high


def test_debt_classification_has_reachable_ordered_bands():
    conservative, maximum = SCHWELLENWERTE["Debt_Equity_konservativ"], SCHWELLENWERTE["Debt_Equity_max"]
    assert 0 <= conservative < maximum
    metric = DebtToEquityCalculator()
    assert metric.classify(conservative) == "Sehr konservativ"
    assert metric.classify(conservative + 1e-9) == "Konservativ"
    assert metric.classify(maximum) == "Konservativ"
    assert metric.classify(maximum + 1e-9) == "Hoch verschuldet"

