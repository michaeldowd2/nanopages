#!/usr/bin/env python3
"""
News Aggregator for FX Portfolio
Fetches news from RSS feeds and NewsAPI
Filters for currency relevance and stores clean JSON
"""

import json
import urllib.request
import urllib.parse
import re
import html
import os
import sys
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET
from email.utils import parsedate_to_datetime

# Add scripts directory to path for imports
sys.path.append(os.path.dirname(__file__))
from utilities.env_loader import get_newsapi_key

# Currency keywords for relevance filtering
CURRENCY_KEYWORDS = {
    "EUR": ["euro", "eur", "ecb", "european central bank", "lagarde", "eurozone", "euro area"],
    "USD": ["dollar", "usd", "federal reserve", "fed", "powell", "us economy", "united states"],
    "GBP": ["pound", "gbp", "sterling", "bank of england", "boe", "uk economy", "britain"],
    "JPY": ["yen", "jpy", "bank of japan", "boj", "japan economy", "tokyo"],
    "CHF": ["franc", "chf", "swiss", "snb", "switzerland"],
    "AUD": ["aussie", "aud", "rba", "australia", "australian dollar"],
    "CAD": ["loonie", "cad", "boc", "canada", "canadian dollar"],
    "NOK": ["krone", "nok", "norway", "norwegian"],
    "SEK": ["krona", "sek", "sweden", "swedish", "riksbank"],
    "CNY": ["yuan", "cny", "rmb", "china", "pboc", "chinese"],
    "MXN": ["peso", "mxn", "mexico", "mexican", "banxico"]
}

def fetch_rss(url, user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'):
    """Fetch RSS feed content with full browser User-Agent to avoid blocking"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': user_agent})
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def parse_rss(xml_content, source_name='RSS'):
    """Parse RSS XML and extract articles

    Note: We use the retrieval date (today) as the effective publication date.
    For fresh news aggregation, this is accurate enough - if we're fetching it today,
    it was published today or very recently.
    """
    articles = []
    cutoff_date = datetime.now() - timedelta(days=30)

    try:
        root = ET.fromstring(xml_content)
        for item in root.findall('.//item'):
            title = item.findtext('title', '')
            link = item.findtext('link', '')
            description = item.findtext('description', '')
            pub_date = item.findtext('pubDate', '')

            # Check if article is too old (for filtering, not storage)
            # We still use pubDate for filtering but don't store it
            try:
                if pub_date:
                    dt = parsedate_to_datetime(pub_date)
                    # Skip articles older than 30 days
                    if dt < cutoff_date:
                        continue
            except Exception:
                pass  # If parsing fails, include the article anyway

            # Clean HTML from description
            description = html.unescape(description)
            description = re.sub(r'<[^>]+>', '', description)
            description = re.sub(r'\s+', ' ', description).strip()

            articles.append({
                'title': title,
                'url': link,
                'snippet': description[:500],  # Max 500 chars
                'source': source_name
            })
    except Exception as e:
        print(f"Error parsing RSS: {e}")

    return articles

def calculate_relevance(text, currency):
    """Calculate relevance score (0-1) for a currency"""
    text_lower = text.lower()
    keywords = CURRENCY_KEYWORDS.get(currency, [])

    # Count keyword matches
    matches = sum(1 for kw in keywords if kw in text_lower)

    # Normalize score (0-1)
    score = min(matches / 3.0, 1.0)  # 3+ matches = 1.0

    return score

def detect_fx_pair_in_text(text):
    """
    Detect FX pair mentions (e.g., "AUD/USD", "EUR/GBP")
    Returns list of (base, quote) tuples
    """
    import re
    pattern = r'\b([A-Z]{3})/([A-Z]{3})\b'
    matches = re.findall(pattern, text)
    return matches

def filter_articles_by_currency(articles, currency, min_score=0.3):
    """
    Filter articles relevant to a specific currency

    Enhanced: Also includes articles about FX pairs involving this currency,
    even if the currency keyword score is below threshold
    """
    relevant = []
    for article in articles:
        text = f"{article['title']} {article['snippet']}"
        score = calculate_relevance(text, currency)

        # Check if article mentions an FX pair involving this currency
        pairs = detect_fx_pair_in_text(text)
        in_pair = any(currency in (base, quote) for base, quote in pairs)

        # Include if: keyword score sufficient OR mentioned in FX pair
        if score >= min_score or in_pair:
            # Boost score if currency is in a pair
            if in_pair and score < 0.5:
                score = max(score, 0.5)  # Minimum 0.5 for pair mentions

            article['relevance_score'] = round(score, 2)
            article['currency'] = currency
            relevant.append(article.copy())  # Use copy to avoid mutation

    return relevant

def load_url_index():
    """Load global URL index to track all articles across currencies"""
    import os
    index_file = '/workspace/group/fx-portfolio/data/news/url_index.json'

    if os.path.exists(index_file):
        with open(index_file, 'r') as f:
            return json.load(f)
    return {}

def save_url_index(index):
    """Save global URL index"""
    import os
    index_file = '/workspace/group/fx-portfolio/data/news/url_index.json'
    with open(index_file, 'w') as f:
        json.dump(index, f, indent=2)

def clean_old_articles():
    """
    Remove article files older than 30 days from storage

    Note: We now use the file date (date key) as the publication date,
    so we just check file dates instead of parsing individual article timestamps.
    """
    import os
    import glob
    cutoff_date = datetime.now() - timedelta(days=30)

    for currency_dir in glob.glob('/workspace/group/fx-portfolio/data/news/*/'):
        for filepath in glob.glob(f'{currency_dir}*.json'):
            if 'url_index' in filepath or 'sources' in filepath:
                continue

            try:
                # Extract date from filename: YYYY-MM-DD.json
                filename = os.path.basename(filepath)
                date_str = filename.replace('.json', '')

                try:
                    file_date = datetime.fromisoformat(date_str)

                    # Remove file if older than 30 days
                    if file_date < cutoff_date:
                        os.remove(filepath)
                        print(f"  Removed old file: {filepath}")
                except ValueError:
                    # Not a date-based filename, skip
                    pass

            except Exception as e:
                print(f"  Error cleaning {filepath}: {e}")

def fetch_from_newsapi(query, max_results=20):
    """
    Fetch articles from NewsAPI.org

    Free tier limit: 100 requests/day
    Be conservative: use max 2-3 queries per day with ~20 results each
    """
    api_key = get_newsapi_key()

    if not api_key:
        print("  ⚠️ NewsAPI key not found in environment (NEWSAPI_APIKEY)")
        print("     Set it in /workspace/project/.env file")
        return []

    articles = []
    cutoff_date = datetime.now() - timedelta(days=30)

    try:
        # Build request URL
        params = urllib.parse.urlencode({
            'q': query,
            'language': 'en',
            'sortBy': 'publishedAt',
            'pageSize': max_results,
            'apiKey': api_key
        })

        url = f"https://newsapi.org/v2/everything?{params}"

        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode())

        if data.get('status') != 'ok':
            error_msg = data.get('message', 'Unknown error')
            print(f"  ⚠️ NewsAPI error: {error_msg}")
            return []

        # Parse articles
        for item in data.get('articles', []):
            # Check if article is too old (for filtering, not storage)
            # We use publishedAt for filtering but don't store it
            published_str = item.get('publishedAt', '')
            try:
                if published_str:
                    # NewsAPI returns ISO 8601: "2026-02-24T12:00:00Z"
                    dt = datetime.fromisoformat(published_str.replace('Z', '+00:00'))

                    # Skip old articles
                    if dt.replace(tzinfo=None) < cutoff_date:
                        continue
            except Exception:
                pass  # If parsing fails, include the article anyway

            # Clean description/content
            description = item.get('description') or item.get('content') or ''
            description = html.unescape(description)
            description = re.sub(r'<[^>]+>', '', description)
            description = re.sub(r'\s+', ' ', description).strip()

            articles.append({
                'title': item.get('title', ''),
                'url': item.get('url', ''),
                'snippet': description[:500],
                'source': f"NewsAPI ({item.get('source', {}).get('name', 'unknown')})"
            })

        print(f"  ✓ NewsAPI: Found {len(articles)} articles for query '{query}'")
        return articles

    except urllib.error.HTTPError as e:
        if e.code == 426:
            print(f"  ✗ NewsAPI: Rate limit exceeded (100 requests/day)")
        elif e.code == 401:
            print(f"  ✗ NewsAPI: Invalid API key")
        else:
            print(f"  ✗ NewsAPI HTTP error {e.code}: {e.reason}")
        return []
    except Exception as e:
        print(f"  ⚠️ NewsAPI error: {e}")
        return []

def save_daily_news(currency, articles, url_index, date_str=None):
    """Save articles to daily JSON file"""
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    output_dir = f'/workspace/group/fx-portfolio/data/news/{currency}'
    import os
    os.makedirs(output_dir, exist_ok=True)

    filepath = f'{output_dir}/{date_str}.json'

    # Load existing if present
    existing_data = {'currency': currency, 'date': date_str, 'articles': []}
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            existing_data = json.load(f)

    # Deduplicate by URL (check both local and global index)
    existing_urls = {a['url'] for a in existing_data['articles']}
    new_articles = []

    for a in articles:
        url = a['url']
        # Skip if already exists locally or in global index
        if url in existing_urls or url in url_index:
            continue

        new_articles.append(a)
        # Add to global index with date key (matches the file date)
        url_index[url] = {
            'currency': currency,
            'first_seen_date': date_str  # Use date string, not full timestamp
        }

    # Add new articles
    existing_data['articles'].extend(new_articles)

    # Generate combined text for LLM analysis
    combined = '\n\n'.join([
        f"[{a.get('relevance_score', 0):.2f}] {a['title']}\n{a['snippet']}"
        for a in existing_data['articles']
    ])
    existing_data['combined_text'] = combined

    # Save
    with open(filepath, 'w') as f:
        json.dump(existing_data, f, indent=2)

    return len(new_articles)

def main():
    """Main aggregation function"""
    print("="*60)
    print("FX News Aggregator")
    print("="*60)

    # Load global URL index
    print("\nLoading URL index...")
    url_index = load_url_index()
    print(f"  Loaded {len(url_index)} previously seen URLs")

    # Clean old articles (>30 days)
    print("\nCleaning articles older than 30 days...")
    clean_old_articles()

    # Load sources
    with open('/workspace/group/fx-portfolio/data/news/sources.json') as f:
        sources = json.load(f)

    all_articles = []

    # Fetch RSS feeds
    for url in sources['rss_feeds']:
        print(f"\nFetching: {url}")

        # Determine source name from URL
        source_name = 'RSS'
        if 'forexlive' in url or 'investinglive' in url:
            source_name = 'ForexLive'
        elif 'fxstreet' in url:
            source_name = 'FXStreet'
        elif 'marketwatch' in url:
            source_name = 'MarketWatch'
        elif 'yahoo' in url or 'finance.yahoo.com' in url:
            source_name = 'Yahoo Finance'
        elif 'investing.com' in url:
            source_name = 'Investing.com'
        elif 'dailyfx' in url:
            source_name = 'DailyFX'

        xml = fetch_rss(url)
        if xml:
            articles = parse_rss(xml, source_name=source_name)
            all_articles.extend(articles)
            print(f"  ✓ Found {len(articles)} articles (within 30 days)")

    # Fetch Reddit RSS (if any configured)
    for url in sources.get('reddit_rss', []):
        print(f"\nFetching: {url}")
        xml = fetch_rss(url)
        if xml:
            articles = parse_rss(xml, source_name='Reddit')
            all_articles.extend(articles)
            print(f"  ✓ Found {len(articles)} posts (within 30 days)")

    # Fetch from NewsAPI (if enabled)
    if sources.get('newsapi_enabled', False):
        print(f"\n{'='*60}")
        print("Fetching from NewsAPI.org")
        print(f"{'='*60}")

        queries = sources.get('newsapi_queries', ['forex'])
        max_per_query = sources.get('newsapi_max_results_per_query', 20)

        total_newsapi_count = 0
        for query in queries:
            print(f"\nQuery: '{query}'")
            newsapi_articles = fetch_from_newsapi(query, max_results=max_per_query)
            all_articles.extend(newsapi_articles)
            total_newsapi_count += len(newsapi_articles)

        print(f"\n  Total from NewsAPI: {total_newsapi_count} articles")
        print(f"  API requests used: {len(queries)} of 100/day limit")

    print(f"\n{'='*60}")
    print(f"Total articles fetched: {len(all_articles)}")
    print(f"{'='*60}\n")

    # Filter by currency and save
    currencies = ["EUR", "USD", "GBP", "JPY", "CHF", "AUD", "CAD", "NOK", "SEK", "CNY", "MXN"]

    for currency in currencies:
        relevant = filter_articles_by_currency(all_articles, currency)
        count = save_daily_news(currency, relevant, url_index)
        print(f"{currency}: {count} new relevant articles (total: {len(relevant)})")

    # Save updated URL index
    save_url_index(url_index)
    print(f"\n✓ URL index updated ({len(url_index)} total URLs tracked)")

    print(f"\n{'='*60}")
    print("✓ News aggregation complete")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
