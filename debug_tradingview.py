import httpx
import asyncio
import json

async def test_tradingview(query):
    url = f"https://symbol-search.tradingview.com/symbol_search/?text={query}&type=&exchange="
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://www.tradingview.com/"
    }
    
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        print(f"Testing TradingView for {query}...")
        try:
            response = await client.get(url)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                print("Success!")
                print(json.dumps(response.json(), indent=2)[:1000])
            else:
                print(f"Error response: {response.text}")
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_tradingview("VOO"))
