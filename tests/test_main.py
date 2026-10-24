"""Regression tests for saving analysis results, without market-data requests."""

from datetime import datetime
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

import src.main as main_module


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    clock = Mock()
    clock.now.return_value = datetime(2026, 10, 24, 23, 19, 3)
    monkeypatch.setattr(main_module, "datetime", clock)


@pytest.mark.parametrize("prefix_type", [str, Path])
@pytest.mark.parametrize("directory_exists", [False, True])
def test_store_results_creates_parent_directories_and_writes_json(
    tmp_path, prefix_type, directory_exists,
):
    directory = tmp_path / "nested" / "compounder_analysis"
    if directory_exists:
        directory.mkdir(parents=True)
    results = {"Münchener Rück": {"kennzahlen": {"ROE": {"wert": 0.18}}}}

    output = main_module._store_results_to_json(
        results, prefix_type(directory / "results"),
    )

    expected = directory / "results_20261024_231903.json"
    assert output == expected
    assert json.loads(expected.read_text(encoding="utf-8")) == results


def test_relative_custom_prefix_remains_relative_to_callers_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    output = main_module._store_results_to_json({}, "reports/results")

    assert output == Path("reports/results_20261024_231903.json")
    assert json.loads((tmp_path / output).read_text(encoding="utf-8")) == {}


def test_default_results_prefix_is_anchored_to_project_not_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert main_module.__file__ is not None
    expected = Path(main_module.__file__).resolve().parents[1] / "compounder_analysis" / "results"
    assert main_module.DEFAULT_RESULTS_PREFIX == expected
    assert main_module.DEFAULT_RESULTS_PREFIX.is_absolute()


def test_main_analyzes_ticker_mapping_and_uses_default_output(tmp_path, monkeypatch, capsys):
    tickers = {"Company A": "AAA", "Company B": "BBB"}
    results = {"Company A": {"symbol": "AAA"}}
    analyze = Mock(return_value=results)
    output_path = tmp_path / "results.json"
    store = Mock(return_value=output_path)
    monkeypatch.setattr(main_module, "extract_all_tickers", lambda: tickers)
    monkeypatch.setattr(main_module, "analyze_batch", analyze)
    monkeypatch.setattr(main_module, "_store_results_to_json", store)
    monkeypatch.chdir(tmp_path)

    main_module.main()

    analyze.assert_called_once_with(tickers)
    store.assert_called_once_with(results, main_module.DEFAULT_RESULTS_PREFIX)
    assert str(output_path) in capsys.readouterr().out

