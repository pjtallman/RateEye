import httpx
import asyncio
import json

async def test_chart_v8(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        print(f"Testing chart v8 for {symbol}...")
        try:
            response = await client.get(url)
            print(f"Status Code: {response.status_code}")
            if response.status_code != 200:
                print(f"Response Text: {response.text}")
                return
            
            data = response.json()
            meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
            if not meta:
                print("No meta found in chart response.")
                print(json.dumps(data, indent=2))
            else:
                print("Successfully found data!")
                print(json.dumps(meta, indent=2))
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_chart_v8("VOO"))
