from src.analysis import analyze_batch
from src.symbols import extract_all_tickers
import json
from datetime import datetime


def main():
    tickers = extract_all_tickers()
    sorted_results = analyze_batch(tickers)
    _store_results_to_json(sorted_results, "../compounder_analysis/results")


def _store_results_to_json(results, filename_prefix):
    current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{current_datetime}.json"
    with open(filename, "w") as f:
        json.dump(results, f, indent=4)

if __name__ == "__main__":

    main()