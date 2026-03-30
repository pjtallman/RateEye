import httpx
import asyncio
import json

async def test_quote_v7(symbol):
    url = f"https://query2.finance.yahoo.com/v7/finance/quote?symbols={symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    async with httpx.AsyncClient(headers=headers) as client:
        print(f"Testing quote v7 for {symbol}...")
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
    asyncio.run(test_quote_v7("VOO"))
