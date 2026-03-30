import httpx
import asyncio
import json

async def test_google_finance(query):
    # Google Finance suggestion API
    url = f"https://www.google.com/finance/_/ticker/s/search?q={query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        print(f"Testing Google Finance for {query}...")
        try:
            response = await client.get(url)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                # Response is often prefixed with )]}'
                text = response.text
                if text.startswith(")]}'"):
                    text = text[4:].strip()
                data = json.loads(text)
                print("Success! Data snippet:")
                print(json.dumps(data, indent=2)[:1000])
            else:
                print(f"Error response: {response.text}")
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_google_finance("VOO"))
