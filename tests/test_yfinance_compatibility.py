"""Exercise the dependency path that triggered the pandas warning, offline."""

import json
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest
from yfinance.scrapers.fundamentals import Financials


@pytest.mark.filterwarnings("error")
@pytest.mark.parametrize("timescale, prefix", [
    ("yearly", "annual"),
    ("quarterly", "quarterly"),
    ("trailing", "trailing"),
])
def test_fundamentals_time_series_has_no_pandas_deprecation_warning(timescale, prefix):
    date = pd.Timestamp("2024-12-31")
    response = {"timeseries": {"result": [{
        "meta": {},
        "timestamp": [int(date.timestamp())],
        f"{prefix}TotalRevenue": [{
            "asOfDate": "2024-12-31", "reportedValue": {"raw": 100.0},
        }],
    }]}}
    data = Mock()
    data.cache_get.return_value = SimpleNamespace(text=json.dumps(response))
    financials = Financials(data, "TEST")

    result = financials._get_financials_time_series(timescale, ["TotalRevenue"])

    assert result.loc["TotalRevenue", date] == 100.0
    data.cache_get.assert_called_once()
    assert "period2=" in data.cache_get.call_args.kwargs["url"]

