from curl_cffi import requests
import json

def test_yahoo_curl_cffi(query):
    url = "https://query2.finance.yahoo.com/v1/finance/search"
    params = {
        "q": query,
        "quotesCount": 10,
        "newsCount": 0
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    print(f"Testing Yahoo Search with curl_cffi for {query}...")
    try:
        response = requests.get(url, params=params, headers=headers, impersonate="chrome110")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Success! Data snippet:")
            print(json.dumps(response.json(), indent=2)[:1000])
        else:
            print(f"Error response: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_yahoo_curl_cffi("VOO")
