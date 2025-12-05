"""
News Service
Fetches real-time news from Google News RSS
"""
import feedparser
import urllib.parse
from typing import List, Dict
from datetime import datetime

class NewsService:
    def __init__(self):
        self.base_url = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
        self.categories = {
            "ALL": "cryptocurrency OR bitcoin OR finance OR politics OR technology",
            "CRYPTO": "cryptocurrency OR bitcoin OR ethereum OR polymarket OR prediction markets",
            "FINANCE": "finance OR stock market OR economy OR federal reserve",
            "TECH": "technology OR artificial intelligence OR startup OR tech news",
            "POLITICS": "politics OR election OR congress OR white house",
            "WORLD": "world news OR international relations OR geopolitics"
        }
    
    def fetch_news(self, limit: int = 10, topic: str = "ALL") -> List[Dict]:
        """Fetch top news headlines from configured topics."""
        all_news = []
        seen_titles = set()
        
        # Get query for topic, default to ALL if not found
        query = self.categories.get(topic.upper(), self.categories["ALL"])
        encoded_query = urllib.parse.quote(query)
        url = self.base_url.format(query=encoded_query)
        
        print(f"Fetching news for topic '{topic}': {url}")
        
        try:
            # Google News often blocks default User-Agents
            # We need to fetch the content first with a browser-like UA
            import requests
            import io
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            print(f"Feed fetch status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"Error fetching feed: {response.text[:200]}")
                return []
                
            # Parse the content
            feed = feedparser.parse(io.BytesIO(response.content))
            print(f"Parsed {len(feed.entries)} entries")
            
            for entry in feed.entries:
                if len(all_news) >= limit:
                    break
                
                title = entry.title
                
                # Deduplicate
                if title in seen_titles:
                    continue
                seen_titles.add(title)
                
                # Parse date
                published = entry.get('published', '')
                try:
                    # Try to parse standard RSS date format
                    # e.g. "Thu, 04 Dec 2025 22:00:00 GMT"
                    dt = datetime.strptime(published, "%a, %d %b %Y %H:%M:%S %Z")
                    timestamp = dt.isoformat()
                except:
                    timestamp = datetime.now().isoformat()
                
                all_news.append({
                    "headline": title,
                    "source": entry.get('source', {}).get('title', 'Google News'),
                    "url": entry.link,
                    "timestamp": timestamp
                })
                
        except Exception as e:
            print(f"Error fetching news: {e}")
            
        return all_news

# Global instance
news_service = NewsService()
