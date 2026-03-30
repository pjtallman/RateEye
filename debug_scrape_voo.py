import httpx
import asyncio
from bs4 import BeautifulSoup
import json
import logging

# Re-test page scraping with better headers and a real symbol
async def test_scrape_voo():
    symbol = "VOO"
    url = f"https://finance.yahoo.com/quote/{symbol}"
    # Use headers that look like a real browser even more
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
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
            
            # 1. Try to find the title/name
            name = soup.find("h1")
            print(f"Found Name: {name.text if name else 'Not found'}")

            # 2. Try to find price
            # Yahoo often embeds data in a JSON script tag or specific data-test attributes
            price = soup.find("fin-streamer", {"data-field": "regularMarketPrice"})
            print(f"Found Price: {price.text if price else 'Not found'}")

            # 3. If price not found, check for the big bold price
            if not price:
                price_alt = soup.find("span", {"data-test": "qsp-price"})
                print(f"Found Price (alt): {price_alt.text if price_alt else 'Not found'}")

        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_scrape_voo())
