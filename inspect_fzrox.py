import yfinance as yf
import json

def inspect_all_keys(symbol):
    print(f"--- All keys for {symbol} ---")
    ticker = yf.Ticker(symbol)
    info = ticker.info
    # Sort and print keys
    for k in sorted(info.keys()):
        print(f"  {k}: {info[k]}")

if __name__ == "__main__":
    inspect_all_keys("FZROX")
