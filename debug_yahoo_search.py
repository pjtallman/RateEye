import httpx
import asyncio
import json

async def test_search_v1(query):
    url = "https://query2.finance.yahoo.com/v1/finance/search"
    params = {
        "q": query,
        "quotesCount": 5,
        "newsCount": 0
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        print(f"Testing search v1 for {query}...")
        try:
            response = await client.get(url, params=params)
            print(f"Status Code: {response.status_code}")
            if response.status_code != 200:
                print(f"Response Text: {response.text}")
                return
            
            data = response.json()
            quotes = data.get("quotes", [])
            if not quotes:
                print("No quotes found in search response.")
                print(json.dumps(data, indent=2))
            else:
                print(f"Successfully found {len(quotes)} quotes!")
                print(json.dumps(quotes[0], indent=2))
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_search_v1("VOO"))
