from pytickersymbols import PyTickerSymbols
from typing import Dict, Any, Optional, List


# countries = stock_data.get_all_countries()
# indices = stock_data.get_all_indices()
# industries = stock_data.get_all_industries()


def extract_all_tickers() -> List:
    indexes = [
        "AEX",
        "BEL 20",
        "CAC 40",
        "DAX",
        "DOW JONES",
        "FTSE 100",
        "IBEX 35",
        "MDAX",
        "NASDAQ 100",
        "OMX Helsinki 15",
        "OMX Helsinki 25",
        "OMX Stockholm 30",
        "S & P 100",
        "S & P 500",
        "SDAX",
        "SMI",
        "TECDAX",
        # "MOEX", no russia
    ]
    all_tickers = {}
    for index in indexes:
        tickers = extract_index_members(index)
        all_tickers.update(tickers)

    return all_tickers

def extract_index_members(index_name: str) -> List:
    stock_data = PyTickerSymbols()
    stocks_in_index = stock_data.get_stocks_by_index(index_name)
    yahoo_tickers = {}
    for stock in stocks_in_index:
        name = extract_ticker_name(stock)
        yahoo_symbol = extract_yahoo_symbol(stock)
        if yahoo_symbol:
            yahoo_tickers[name] = yahoo_symbol
    return yahoo_tickers

def extract_ticker_name(pyticker: Dict[str, Any]) -> str:
    return pyticker.get("name")

def extract_yahoo_symbol(pyticker: Dict[str, Any]) -> Optional[str]:
    symbols = pyticker.get("symbols")
    if not symbols:
        print("No symbols found for ticker:", pyticker)
        return None
    return pyticker.get("symbols", [{}])[0].get("yahoo")


if __name__ == "__main__":
    tickers = extract_index_members("DAX")

    # tickers = extract_all_tickers()
    print(tickers)