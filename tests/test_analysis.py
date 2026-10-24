"""Offline integration checks for the calculator results consumed by screening."""

from types import SimpleNamespace

import pandas as pd
import pytest

from src.analysis import (
    _analyze_compounder,
    _calculate_average_performance,
    _normalize_for_ranking,
)


def test_all_six_metrics_contribute_to_screening_and_ranking():
    dates = pd.to_datetime(["2024-12-31", "2023-12-31", "2022-12-31"])

    def frame(rows):
        return pd.DataFrame.from_dict(rows, orient="index", columns=dates)

    company = SimpleNamespace(
        ticker="TEST",
        info={"returnOnEquity": 0.2},
        financials=frame({
            "Operating Income": [32, 28, 24],
            "Pretax Income": [32, 28, 24],
            "Tax Provision": [8, 7, 6],
            "Total Revenue": [100, 80, 64],
            "Diluted EPS": [2.88, 2.4, 2.0],
        }),
        balance_sheet=frame({
            "Stockholders Equity": [100, 80, 70],
            "Total Debt": [60, 50, 40],
            "Long Term Debt": [40, 30, 20],
            "Current Debt": [20, 20, 20],
            "Cash And Cash Equivalents": [30, 20, 10],
        }),
        cashflow=frame({"Free Cash Flow": [12, 10, 8]}),
    )
    result = _analyze_compounder(company)
    expected = {
        "ROE": 0.2, "ROIC": 0.2, "FCF_Margin": 0.12,
        "Revenue_Growth": 0.25, "EPS_Growth": 0.2, "Debt_to_Equity": 0.6,
    }
    assert result["symbol"] == "TEST"
    for metric, value in expected.items():
        assert result["kennzahlen"][metric]["wert"] == pytest.approx(value)
    assert all(result["erfuellt_kriterien"].values())
    summary = result["gesamtbewertung"]
    assert summary["erfuellte_kriterien"] == 6
    assert summary["erfolgsquote"] == 1
    assert summary["compounder_qualitaet"] == "Exzellenter Compounder"
    expected_performance = (0.2 / 0.6 + 0.2 / 0.6 + 0.12 / 0.5 + 0.25 / 0.5 + 0.2 / 0.5 + 0.6) / 6
    assert summary["durchschnittliche_performance"] == pytest.approx(expected_performance)
    assert summary["rank_score"] == pytest.approx(0.7 + 0.3 * expected_performance)


def test_debt_criterion_maps_to_the_actual_metric_name():
    results = {
        "kennzahlen": {"Debt_to_Equity": {"wert": 0.6}},
        "erfuellt_kriterien": {"Debt_Equity_ok": True},
    }
    assert _calculate_average_performance(results) == pytest.approx(0.6)


def test_explicit_zero_debt_gets_best_leverage_ranking_not_worst():
    assert _normalize_for_ranking("Debt_to_Equity", 0.0) == 1.0
    assert _normalize_for_ranking("Debt_to_Equity", None) == 0.0
    assert _normalize_for_ranking("ROE", 0.0) == 0.0


def test_missing_financials_do_not_satisfy_any_screening_criteria():
    company = SimpleNamespace(ticker="EMPTY", info={}, financials=pd.DataFrame(),
                              balance_sheet=pd.DataFrame(), cashflow=pd.DataFrame())
    result = _analyze_compounder(company)
    assert not any(result["erfuellt_kriterien"].values())
    assert all(data["wert"] is None for data in result["kennzahlen"].values())
    assert result["gesamtbewertung"]["rank_score"] == 0
