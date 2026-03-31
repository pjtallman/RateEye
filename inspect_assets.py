import yfinance as yf
import json

def inspect_asset_info(symbol):
    print(f"--- Inspecting {symbol} ---")
    ticker = yf.Ticker(symbol)
    info = ticker.info
    # Common keys that might help identify asset class
    keys = ['category', 'quoteType', 'morningStarRiskRating', 'morningStarOverallRating', 
            'fundFamily', 'legalType', 'marketCap', 'totalAssets']
    for k in keys:
        if k in info:
            print(f"  {k}: {info[k]}")
    
    # Print all keys if we're still unsure
    # print(info.keys())

if __name__ == "__main__":
    inspect_asset_info("VBR")   # Small Cap Value
    print("\n")
    inspect_asset_info("FZROX") # Large Cap (Total Market)
    print("\n")
    inspect_asset_info("VOO")   # Large Cap
