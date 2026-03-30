import json
import logging
import asyncio
import random
from typing import List, Dict, Optional, Any
from database import SecurityType, AssetClass
import yfinance as yf
from curl_cffi.requests import AsyncSession

logger = logging.getLogger(__name__)

class YahooFinanceScraper:
    """
    Highly robust scraper for Yahoo Finance metadata using curl_cffi to bypass bot detection.
    """
    SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Origin": "https://finance.yahoo.com",
        "Referer": "https://finance.yahoo.com/"
    }

    async def search(self, query: str) -> List[Dict[str, str]]:
        """
        Search for securities by name or symbol using curl_cffi for reliability.
        """
        params = {
            "q": query,
            "quotesCount": 20,
            "newsCount": 0
        }
        
        try:
            async with AsyncSession(impersonate="chrome110") as s:
                # Small random delay to avoid bot detection
                await asyncio.sleep(random.uniform(0.1, 0.3))
                
                response = await s.get(self.SEARCH_URL, params=params, headers=self.HEADERS)
                
                if response.status_code == 429:
                    logger.warning(f"Yahoo search rate limited (429) for '{query}'")
                    raise Exception("Rate limited")
                
                if response.status_code != 200:
                    logger.error(f"Yahoo search failed with status {response.status_code}")
                    return []
                
                data = response.json()
                results = []
                for quote in data.get("quotes", []):
                    results.append({
                        "symbol": quote.get("symbol"),
                        "name": quote.get("shortname") or quote.get("longname") or quote.get("symbol"),
                        "type": quote.get("quoteType"),
                        "exchange": quote.get("exchange")
                    })
                return results
        except Exception as e:
            logger.error(f"Search error: {e}")
            # Differentiate error vs empty result by re-raising if it's a rate limit
            if "Rate limited" in str(e):
                raise
            return []

    async def lookup(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed metadata using yfinance which is very reliable for quotes.
        """
        try:
            # Wrap synchronous yfinance call
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: yf.Ticker(symbol).info)
            
            if not info or 'symbol' not in info:
                logger.warning(f"yfinance returned no info for '{symbol}'")
                return None
            
            return {
                "symbol": symbol,
                "name": info.get("longName") or info.get("shortName") or symbol,
                "security_type": self._map_security_type(info.get("quoteType")),
                "asset_class": self._infer_asset_class(info),
                "current_price": str(info.get("regularMarketPrice", "")),
                "previous_close": str(info.get("regularMarketPreviousClose", "")),
                "open_price": str(info.get("regularMarketOpen", "")),
                "nav": str(info.get("navPrice", "")),
                "range_52_week": info.get("fiftyTwoWeekRange", ""),
                "avg_volume": str(info.get("averageDailyVolume3Month", "")),
                "yield_30_day": str(info.get("trailingAnnualDividendYield", "")),
                "yield_7_day": ""
            }
        except Exception as e:
            logger.error(f"Lookup error for '{symbol}': {e}")
            return None

    def _map_security_type(self, yahoo_type: str) -> str:
        mapping = {
            "EQUITY": SecurityType.STOCK.value,
            "ETF": SecurityType.ETF.value,
            "MUTUALFUND": SecurityType.MUTUAL_FUND.value,
            "MONEYMARKET": SecurityType.MONEY_MARKET.value,
            "BOND": SecurityType.BOND.value
        }
        return mapping.get(yahoo_type, SecurityType.STOCK.value)

    def _infer_asset_class(self, info: Dict) -> Optional[str]:
        y_type = info.get("quoteType")
        if y_type == "MONEYMARKET":
            return AssetClass.MONEY_MARKET.value
        if y_type == "EQUITY":
            return AssetClass.LARGE_CAP_STOCK.value
        return None
