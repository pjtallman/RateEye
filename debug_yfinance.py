import yfinance as yf
import json

def test_yfinance(symbol):
    print(f"Testing yfinance for {symbol}...")
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        if not info:
            print("No info found.")
            return
        
        print("Success! Data snippet:")
        # Print a few fields
        print(f"Short Name: {info.get('shortName')}")
        print(f"Long Name: {info.get('longName')}")
        print(f"Quote Type: {info.get('quoteType')}")
        print(f"Regular Market Price: {info.get('regularMarketPrice')}")
        
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_yfinance("VOO")
