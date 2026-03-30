import httpx
import asyncio
from bs4 import BeautifulSoup
import json

async def test_scrape_page(symbol):
    url = f"https://finance.yahoo.com/quote/{symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        print(f"Testing page scrape for {symbol}...")
        try:
            response = await client.get(url)
            print(f"Status Code: {response.status_code}")
            if response.status_code != 200:
                print(f"Response Text snippet: {response.text[:500]}")
                return
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Try to find price
            price = soup.find("fin-streamer", {"data-field": "regularMarketPrice"})
            if price:
                print(f"Found Price: {price.text}")
            else:
                # Alternate search for price
                price = soup.find("span", {"data-test": "qsp-price"})
                print(f"Found Price (alt): {price.text if price else 'Not found'}")

            # Try to find name
            name = soup.find("h1")
            if name:
                print(f"Found Name: {name.text}")

        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_scrape_page("VOO"))
