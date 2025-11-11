from pytickersymbols import PyTickerSymbols
from typing import Dict, Any, Optional, List


# countries = stock_data.get_all_countries()
# indices = stock_data.get_all_indices()
# industries = stock_data.get_all_industries()

def extract_index_members(index_name: str) -> List:
    stock_data = PyTickerSymbols()
    stocks_in_index = stock_data.get_stocks_by_index(index_name)
    yahoo_tickers = {}
    for stock in stocks_in_index:
        name = extract_ticker_name(stock)
        yahoo_symbol = extract_yahoo_symbol(stock)
        yahoo_tickers[name] = yahoo_symbol
        print(f"Name: {name}, Yahoo Symbol: {yahoo_symbol}")

    return yahoo_tickers

def extract_ticker_name(pyticker: Dict[str, Any]) -> str:
    return pyticker.get("name")

def extract_yahoo_symbol(pyticker: Dict[str, Any]) -> Optional[str]:
    return pyticker.get("symbols", [{}])[0].get("yahoo")

if __name__ == "__main__":
    tickers = extract_index_members("DAX")
    print(tickers)