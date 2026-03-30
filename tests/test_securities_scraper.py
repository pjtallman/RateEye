import pytest
import json
from unittest.mock import AsyncMock, patch
from src.rateeye.securities.scraper import YahooFinanceScraper
from database import SecurityType, AssetClass

@pytest.mark.asyncio
async def test_scraper_search():
    mock_response = {
        "quotes": [
            {"symbol": "VOO", "shortname": "Vanguard S&P 500 ETF", "quoteType": "ETF", "exchange": "NYE"}
        ]
    }
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = AsyncMock(
            status_code=200,
            json=lambda: mock_response,
            raise_for_status=lambda: None
        )
        
        scraper = YahooFinanceScraper()
        results = await scraper.search("VOO")
        
        assert len(results) == 1
        assert results[0]["symbol"] == "VOO"
        assert results[0]["name"] == "Vanguard S&P 500 ETF"
        assert results[0]["type"] == "ETF"

@pytest.mark.asyncio
async def test_scraper_lookup():
    mock_response = {
        "quoteSummary": {
            "result": [{
                "price": {
                    "quoteType": "ETF",
                    "longName": "Vanguard S&P 500 ETF",
                    "regularMarketPrice": {"raw": 450.12}
                },
                "summaryDetail": {
                    "previousClose": {"raw": 448.00},
                    "open": {"raw": 449.00},
                    "navPrice": {"raw": 450.10},
                    "fiftyTwoWeekLow": {"raw": 380.00},
                    "fiftyTwoWeekHigh": {"raw": 460.00},
                    "averageVolume": {"raw": 3000000},
                    "yield": {"fmt": "1.5%"}
                }
            }]
        }
    }
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = AsyncMock(
            status_code=200,
            json=lambda: mock_response,
            raise_for_status=lambda: None
        )
        
        scraper = YahooFinanceScraper()
        data = await scraper.lookup("VOO")
        
        assert data is not None
        assert data["symbol"] == "VOO"
        assert data["name"] == "Vanguard S&P 500 ETF"
        assert data["security_type"] == SecurityType.ETF.value
        assert data["current_price"] == "450.12"
        assert data["nav"] == "450.1"
        assert data["yield_30_day"] == "1.5%"
