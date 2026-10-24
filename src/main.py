import json
from datetime import datetime
from pathlib import Path

from src.analysis import analyze_batch
from src.symbols import extract_all_tickers


DEFAULT_RESULTS_PREFIX = Path(__file__).resolve().parents[1] / "compounder_analysis" / "results"


def main():
    tickers = extract_all_tickers()

    print(f"Gefundene Ticker: {len(tickers)}")
    sorted_results = analyze_batch(tickers)
    filename = _store_results_to_json(sorted_results, DEFAULT_RESULTS_PREFIX)
    print(f"Ergebnisse gespeichert: {filename}")


def _store_results_to_json(results, filename_prefix: str | Path) -> Path:
    """Write timestamped JSON, creating missing parent directories as needed."""
    current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = Path(f"{filename_prefix}_{current_datetime}.json")
    filename.parent.mkdir(parents=True, exist_ok=True)
    with filename.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    return filename

if __name__ == "__main__":

    main()