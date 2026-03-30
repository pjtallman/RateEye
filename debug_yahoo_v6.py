import httpx
import asyncio
import json

async def test_quote_v6(symbol):
    url = f"https://query1.finance.yahoo.com/v6/finance/quote?symbols={symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache"
    }
    
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        print(f"Testing quote v6 for {symbol}...")
        try:
            response = await client.get(url)
            print(f"Status Code: {response.status_code}")
            if response.status_code != 200:
                print(f"Response Text: {response.text}")
                return
            
            data = response.json()
            result = data.get("quoteResponse", {}).get("result")
            if not result or len(result) == 0:
                print("No result found in quoteResponse.")
                print(json.dumps(data, indent=2))
            else:
                print("Successfully found data!")
                print(json.dumps(result[0], indent=2))
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_quote_v6("VOO"))
