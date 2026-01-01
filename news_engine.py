
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
import html
import re

# List of RSS Feeds
# List of RSS Feeds
RSS_FEEDS = [
    # --- INDIA FOCUSED ---
    {
        "Source": "MoneyControl (Top News)",
        "URL": "https://www.moneycontrol.com/rss/MCtopnews.xml"
    },
    {
        "Source": "MoneyControl (Business)",
        "URL": "https://www.moneycontrol.com/rss/business.xml"
    },
    {
        "Source": "Economic Times (Markets)",
        "URL": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"
    },
    {
        "Source": "LiveMint (Markets)",
        "URL": "https://www.livemint.com/rss/markets"
    },
    {
        "Source": "Investing.com India",
        "URL": "https://in.investing.com/rss/news_25.rss"  # Indian Stock News
    },
    
    # --- GLOBAL & MACRO ---
    {
        "Source": "Reuters (Business)",
        "URL": "https://feeds.reuters.com/reuters/businessNews"
    },
    {
        "Source": "CNBC International",
        "URL": "https://www.cnbc.com/id/10000664/device/rss/rss.html"
    },
    {
        "Source": "Investing.com Global",
        "URL": "https://www.investing.com/rss/news_1.rss" # Global Markets
    },
    
    # --- CURATED SEARCHES (Alternatives for non-RSS sites like Bloomberg/Tickertape) ---
    {
        "Source": "Google News (Bloomberg Topics)",
        "URL": "https://news.google.com/rss/search?q=site:bloomberg.com+market&hl=en-IN&gl=IN&ceid=IN:en"
    },
    {
        "Source": "Google News (StockEdge/Tickertape)",
        "URL": "https://news.google.com/rss/search?q=Indian+Stock+Analysis+OR+Nifty+50+Fundamental&hl=en-IN&gl=IN&ceid=IN:en"
    },
    
    # --- COMMODITIES ---
    {
        "Source": "Commodity Online",
        "URL": "https://www.commodityonline.com/rss/news"
    }
]

def calculate_sentiment_score(text):
    """
    Calculates detailed sentiment score [-10 to +10].
    """
    score = 0
    text_lower = text.lower()
    
    # Weighted Keywords
    weights = {
        'surge': 3, 'skyrocket': 3, 'jump': 2, 'gain': 2, 'rally': 2, 'hit upper circuit': 4,
        'profit': 2, 'growth': 1, 'record': 2, 'strong': 1, 'dividend': 2, 'buy': 1, 
        'upgrade': 2, 'positive': 1, 'bull': 1,
        
        'crash': -3, 'plunge': -3, 'slump': -2, 'tank': -3, 'fall': -1, 'drop': -1, 
        'loss': -2, 'weak': -1, 'sell': -1, 'debt': -1, 'downgrade': -2, 'negative': -1,
        'bear': -1, 'concern': -1, 'warning': -1
    }
    
    for word, wt in weights.items():
        if word in text_lower:
            score += wt
            
    # Cap score
    score = max(min(score, 10), -10)
    
    label = "Neutral"
    if score >= 2: label = "Positive"
    elif score <= -2: label = "Negative"
    
    return score, label

def fetch_rss_feed(feed_info):
    """
    Fetches and parsed a single RSS feed with Link extraction and Scouting.
    """
    news_items = []
    source_name = feed_info["Source"]
    print(f"Fetching {source_name}...")
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(feed_info["URL"], headers=headers, timeout=5)
        
        if response.status_code == 200:
            try:
                root = ET.fromstring(response.content)
            except: return []

            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            
            for item in root.findall('.//item'): 
                try:
                    title = item.find('title').text
                    if not title: continue
                    
                    description = item.find('description').text or ""
                    link = item.find('link').text or ""
                    pub_date_str = item.find('pubDate').text 
                    
                    if '<' in description: 
                         description = re.sub(re.compile('<.*?>'), '', html.unescape(description))

                    try:
                        pub_dt = parsedate_to_datetime(pub_date_str)
                        pub_date = pub_dt.date() 
                    except:
                        pub_date = today 
                    
                    if pub_date < yesterday: continue
                    
                    score, impact = calculate_sentiment_score(title)
                    
                    news_items.append({
                        "Source": source_name,
                        "Time": pub_dt.strftime("%d-%b %H:%M"),
                        "NumericTime": pub_dt.timestamp(),
                        "Headline": title.strip(),
                        "Impact": impact,
                        "Score": score,
                        "Link": link,
                        "Details": description[:150] + "..." if description else ""
                    })
                except: continue
    except: pass
    return news_items

from difflib import SequenceMatcher

def group_news(news_list):
    """
    Groups similar news headlines together.
    """
    if not news_list: return []
    
    grouped = []
    processed_indices = set()
    
    # Sort by time first
    news_list.sort(key=lambda x: x['NumericTime'], reverse=True)
    
    for i, item in enumerate(news_list):
        if i in processed_indices: continue
        
        current_group = {
            "Headline": item['Headline'],
            "Impact": item['Impact'],
            "Score": item['Score'],
            "Time": item['Time'],
            "Link": item['Link'], 
            "Sources": [item['Source']],
            "RelatedLinks": []
        }
        
        processed_indices.add(i)
        
        # Check against following items
        for j in range(i+1, len(news_list)):
            if j in processed_indices: continue
            
            other = news_list[j]
            ratio = SequenceMatcher(None, item['Headline'].lower(), other['Headline'].lower()).ratio()
            
            # If 45% similarity found (headlines often vary wildly but share keywords)
            if ratio > 0.45:
                # Merge logic: Keep the "Stronger" sentiment or "Newer" one as main?
                # We'll just list additional sources
                if other['Source'] not in current_group['Sources']:
                    current_group['Sources'].append(other['Source'])
                    current_group['RelatedLinks'].append(other['Link'])
                
                # If the other one has a more intense score, verify if we should swap? NO, keep newest.
                processed_indices.add(j)
                
        grouped.append(current_group)
        
    return grouped

def fetch_market_news():
    """
    Aggregates, deduplicates and groups news.
    """
    all_news = []
    seen_urls = set()
    
    for feed in RSS_FEEDS:
        items = fetch_rss_feed(feed)
        for item in items:
            if item['Link'] not in seen_urls:
                seen_urls.add(item['Link'])
                all_news.append(item)
                
    return group_news(all_news)

def fetch_stock_specific_news(ticker):
    """
    Fetches news specifically for the given ticker using Google News RSS.
    """
    from urllib.parse import quote
    
    # Clean ticker (e.g. "TATASTEEL.NS" -> "TATASTEEL")
    clean_ticker = ticker.replace(".NS", "").replace(".BO", "")
    
    # Construct Google News RSS URL
    query = quote(f"{clean_ticker} share news india")
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    
    feed_info = {
        "Source": "Google News",
        "URL": rss_url
    }
    
    # Reuse existing rss parser
    items = fetch_rss_feed(feed_info)
    
    # Deduplicate and basic clean
    # Return top 10 relevant items
    return items[:10]
