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

