import yfinance as yf
import json

def inspect_yields(symbol):
    print(f"--- Inspecting {symbol} ---")
    ticker = yf.Ticker(symbol)
    info = ticker.info
    yield_keys = [k for k in info.keys() if 'yield' in k.lower()]
    for k in yield_keys:
        print(f"  {k}: {info[k]}")
    
    # Also print some common fundamental keys
    others = ['trailingAnnualDividendYield', 'dividendYield', 'ytdReturn', 'fiveYearAvgDividendYield']
    for k in others:
        if k in info:
            print(f"  {k}: {info[k]}")

if __name__ == "__main__":
    inspect_yields("VOO")
    print("\n")
    inspect_yields("VUSXX")
    print("\n")
    inspect_yields("FISXX")
