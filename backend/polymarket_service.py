import requests
from typing import List, Dict

# Polymarket uses different APIs for different data
GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"
DATA_API = "https://data-api.polymarket.com"

def get_all_markets(limit: int = 100) -> List[Dict]:
    """Fetch active markets from Polymarket Gamma API."""
    try:
        response = requests.get(
            f"{GAMMA_API}/markets",
            params={"limit": limit, "active": "true", "closed": "false"}
        )
        print(f"Markets API response status: {response.status_code}")
        if response.status_code == 200:
            markets = response.json()
            print(f"Found {len(markets)} markets")
            # Filter for active, non-closed markets with valid data
            active_markets = [
                m for m in markets 
                if not m.get('closed', False) 
                and m.get('outcomePrices')
                and m.get('question')
            ]
            print(f"Active markets after filter: {len(active_markets)}")
            
            # Parse outcome prices and add probability
            for market in active_markets:
                try:
                    prices = eval(market.get('outcomePrices', '["0.5", "0.5"]'))
                    market['probability'] = float(prices[0]) if prices else 0.5
                    market['title'] = market.get('question', '')
                    market['id'] = market.get('conditionId', market.get('id', ''))
                except:
                    market['probability'] = 0.5
                    market['title'] = market.get('question', '')
            
            return active_markets[:limit]
        return []
    except Exception as e:
        print(f"Error fetching markets: {e}")
        return []

def get_market_by_id(market_id: str) -> Dict:
    """Get a specific market by ID."""
    response = requests.get(f"{GAMMA_API}/markets/{market_id}")
    if response.status_code == 200:
        return response.json()
    return {}

def get_user_positions(wallet: str) -> List[Dict]:
    """Get user's open positions."""
    positions = []
    offset = 0
    
    while True:
        response = requests.get(
            f"{DATA_API}/positions",
            params={"user": wallet, "limit": 100, "offset": offset}
        )
        if response.status_code != 200:
            break
        data = response.json()
        if not data:
            break
        positions.extend(data)
        offset += 100
    
    return positions

def get_user_activity(wallet: str, limit: int = 50) -> List[Dict]:
    """Get user's recent trading activity."""
    response = requests.get(
        f"{DATA_API}/activity",
        params={"user": wallet, "limit": limit}
    )
    if response.status_code == 200:
        return response.json()
    return []
