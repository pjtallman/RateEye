import asyncio
import json
from curl_cffi.requests import AsyncSession
import yfinance as yf

async def debug_symbol(symbol):
    print(f"--- Debugging {symbol} ---")
    
    # 1. Test Search
    search_url = "https://query2.finance.yahoo.com/v1/finance/search"
    params = {"q": symbol, "quotesCount": 10}
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    
    try:
        async with AsyncSession(impersonate="chrome110") as s:
            resp = await s.get(search_url, params=params, headers=headers)
            print(f"Search Status: {resp.status_code}")
            if resp.status_code == 200:
                quotes = resp.json().get("quotes", [])
                print(f"Search found {len(quotes)} results.")
                for q in quotes:
                    print(f"  - {q.get('symbol')}: {q.get('shortname')} ({q.get('quoteType')})")
            else:
                print(f"Search failed: {resp.text}")
    except Exception as e:
        print(f"Search Exception: {e}")

    # 2. Test yfinance lookup
    try:
        print(f"Testing yfinance info for {symbol}...")
        ticker = yf.Ticker(symbol)
        info = ticker.info
        if info and 'symbol' in info:
            print("yfinance Success!")
            print(f"  Name: {info.get('longName') or info.get('shortName')}")
            print(f"  Type: {info.get('quoteType')}")
            print(f"  Price: {info.get('regularMarketPrice')}")
        else:
            print("yfinance returned no valid info.")
    except Exception as e:
        print(f"yfinance Exception: {e}")

if __name__ == "__main__":
    asyncio.run(debug_symbol("VUSXX"))
    print("\n")
    asyncio.run(debug_symbol("FISXX"))
