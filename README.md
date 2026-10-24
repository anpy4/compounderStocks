# compounderStocks
Comgest Compounder Stock picking

## Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and sync the project environment:

```powershell
uv sync --group test
```

Run the tests and application with:

```powershell
uv run --group test pytest
uv run python -m src.main
```

Dependencies are declared in `pyproject.toml` and pinned in `uv.lock`.

Pandas is currently restricted to `>=2.2,<3.0` for compatibility with yfinance
0.2.x, which calls `Timestamp.utcnow()` (deprecated since pandas 3.0). This
avoids the warning without modifying installed libraries or hiding warnings.
Run `uv sync --group test` after updating the project to apply the lockfile.

## Analysis output

The application writes UTF-8 JSON to
`compounder_analysis/results_YYYYMMDD_HHMMSS.json` under the project root.
Missing parent directories are created automatically. The default output path
is independent of the working directory used by the terminal or IDE, and the
saved file path is printed after the analysis finishes. Explicit custom prefixes
passed to `_store_results_to_json` may be strings or `Path` objects; relative
custom prefixes remain relative to the caller's working directory.

## Financial meaning and calculation conventions

Ratios are returned as decimal fractions (`0.15` means 15%). Debt/equity is
a multiple (`0.8` means 0.80 of interest-bearing debt per 1.00 of equity), not
total liabilities/equity. Monetary amounts must use the same currency and units.

| Metric | Business interpretation | Calculation |
| --- | --- | --- |
| ROE | Profit generated for shareholders per unit of their book equity. Buybacks and leverage can increase ROE without improving operations. | Yahoo's reported `returnOnEquity` (TTM), otherwise latest annual net income attributable to shareholders / average opening and closing shareholders' equity. |
| ROIC | After-tax operating return on capital supplied by shareholders and lenders. Compare with the cost of capital, not just a fixed screening threshold. | `Operating income × (1 − tax rate) / average cash-adjusted invested capital`. |
| FCF margin | How much revenue becomes cash after capital investment, available for debt repayment, distributions or reinvestment. | Reported free cash flow / revenue, otherwise `(operating cash flow − abs(capital expenditure)) / revenue`. |
| Revenue growth | Historical expansion of the business, which can also reflect acquisitions, inflation and currency movements. | Arithmetic mean of valid consecutive annual `(current revenue − prior revenue) / prior revenue` changes. |
| EPS growth | Growth in earnings **per share**, including the effects of dilution and buybacks. | Same annual-growth method, preferring reported diluted EPS, then reconstructible diluted EPS, then basic EPS. Reconstruction requires common-shareholder net income and positive weighted-average shares. |
| Debt/equity | Financial leverage measured against shareholders' book equity; lower is generally safer. | Reported total debt / positive shareholders' equity. If total debt is absent, use long-term debt plus current debt, without adding overlapping aliases. |

### Important assumptions and limitations

- Calculations use `yfinance` annual statements (`financials`, `balance_sheet`,
  `cashflow`), not quarterly statements. Periods are sorted by date. Flows and
  balance-sheet values must match the same fiscal year end; adjacent annual
  periods allow 350–380 days to accommodate 52/53-week fiscal years.
- Revenue and EPS growth are **not CAGR**: +50% followed by −20% has an
  arithmetic mean of 15%, but a two-year CAGR of about 9.54%. This preserves
  the original mean-year-on-year screening convention, not compounded growth.
- Invalid annual pairs are skipped without bridging gaps. A positive prior
  value is required: percentage growth from a loss or zero base is not a
  comparable growth measure. EPS may decline into a loss; revenue may fall to
  zero but must not be negative. A valid older pair can still yield a result
  even when the most recent pair is missing.
- EPS forecasts (`forwardEps` versus `trailingEps`) are **not** substituted for
  historical EPS growth. Net-income growth without share counts is **not** EPS
  growth. Reconstructed diluted EPS is an approximation when conversion-related
  numerator adjustments are unavailable; reported EPS is preferred. Provider
  EPS must be adjusted consistently for stock splits across the history.
- ROE's manual fallback requires positive equity at both year ends and excludes
  equity including minority interests. Negative/near-zero equity makes ordinary
  ROE comparisons misleading. A finite provider ROE is accepted as supplied;
  its underlying TTM periods and accounting adjustments are not independently
  audited, and it can differ from the annual fallback.
- ROIC uses operating income or EBIT. A pretax-income-plus-net-interest fallback
  is only an approximation (other non-operating items may remain); missing
  interest income is assumed zero. Reconstructing from revenue requires cost of
  revenue **and total operating expenses**. Partial expense rows or normalized
  net income cannot replace operating income.
- ROIC uses the effective tax rate (`tax provision / positive pretax income`)
  only when it lies between 0% and 100%. Otherwise it uses a **25% normalized
  assumption**, including for losses, tax benefits and exceptional tax charges.
  This is an estimate, not a company-specific statutory tax calculation.
- ROIC defines capital as `equity + interest-bearing debt − cash`, averaged over
  opening and closing year ends. If there is no prior annual balance sheet,
  closing capital alone is used as an approximation. Yahoo's `Invested Capital`
  field is treated as gross equity-plus-debt capital and receives the same cash
  deduction. Undisclosed cash is not deducted. Cash aliases are alternatives,
  not additive; short-term investments are included only in the combined-field
  fallback. Deducting all cash rather than only excess cash is a simplifying
  choice and can materially increase ROIC for cash-rich businesses.
- `Total Capitalization` can omit current debt, while `Total Assets − cash`
  fails to subtract non-interest-bearing operating liabilities. Neither is a
  valid substitute for invested capital. Zero/negative invested capital is
  reported as unavailable rather than a positive quality signal.
- Missing debt is unknown, not zero: either an explicit total (including zero)
  or both current and long-term components are required. The legacy
  `Short Long Term Debt` label is a last-resort current-debt proxy; depending on
  the provider it may cover only current maturities, not all short-term debt.
- Missing/non-finite values produce `(None, reason)` when no supported fallback
  or valid annual pair exists. Negative profits and free cash flows remain
  negative; `abs()` must not turn them into positive performance.

### Screening thresholds versus financial correctness

Thresholds in `src/thresholds.py` are configurable investment-policy choices,
not universal definitions of a good company. The screening limits remain ROE
15%, ROIC 16%, FCF margin 10%, revenue growth 8%, EPS growth 10%, and maximum
debt/equity 0.8. Rating-only bands distinguish strong EPS growth (15%) from good
(10%) and very conservative debt/equity (at most 0.5) from conservative (at most
0.8); the previous equal/reversed bands made intermediate ratings unreachable.

These measures are most comparable across non-financial businesses with similar
accounting policies. Banks and insurers need sector-specific leverage/capital
metrics; leases, goodwill, acquisition accounting and exceptional cash flows can
also distort comparisons. Passing these rules does not establish valuation,
durable competitive advantage or investment suitability.

## Tests

`tests/test_metrics.py` uses hand-calculated financial statements and local
ticker doubles. No Yahoo requests or credentials are needed. It covers formulas,
dilution, sign conventions, date ordering and alignment, missing/invalid data,
fallbacks and inclusive classification boundaries. `tests/test_analysis.py`
checks the six metrics together, screening and ranking. It also guards against
two ranking defects: ignoring debt/equity through a mismatched metric name and
giving zero debt the worst rather than best leverage score. Regression tests
were first run against the old implementations to verify that they detect the
defects.

`tests/test_main.py` covers directory creation, timestamped UTF-8 output, stable
default paths and the mocked application entry point.
`tests/test_yfinance_compatibility.py` exercises yfinance's annual, quarterly and
trailing financial-statement parsing with simulated responses and warnings as
errors, without making network requests.

Run the complete suite, treating warnings as errors:

```powershell
uv run --group test python -m pytest -q -W error
```
