import httpx
import asyncio
import os

async def save_yahoo_page(symbol):
    url = f"https://finance.yahoo.com/quote/{symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache"
    }
    
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        print(f"Saving page for {symbol}...")
        try:
            response = await client.get(url)
            with open("yahoo_response.html", "w") as f:
                f.write(response.text)
            print(f"Status Code: {response.status_code}")
            print(f"Length: {len(response.text)}")
            print(f"Snippet: {response.text[:500]}")
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(save_yahoo_page("VOO"))
