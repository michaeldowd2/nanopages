#!/usr/bin/env python3
"""
Step 3: News Aggregator for FX Portfolio

Fetches news from RSS feeds and NewsAPI, filters for currency relevance,
and stores in CSV format.

Output: CSV with columns: date, source, url, currency, title, snippet
"""

import json
import urllib.request
import urllib.parse
import re
import html
import os
import sys
import argparse
import glob
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET
from email.utils import parsedate_to_datetime

# Add scripts directory to path for imports
sys.path.append('/workspace/group/fx-portfolio/scripts')
from utilities.env_loader import get_newsapi_key
from utilities.config_loader import get_currencies
from utilities.pipeline_logger import PipelineLogger
from utilities.csv_helper import write_csv, read_csv, csv_exists
from utilities.article_id import generate_article_id

CURRENCIES = get_currencies()

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
    """Parse RSS XML and extract articles"""
    articles = []
    cutoff_date = datetime.now() - timedelta(days=30)

    try:
        root = ET.fromstring(xml_content)
        for item in root.findall('.//item'):
            title = item.findtext('title', '')
            link = item.findtext('link', '')
            description = item.findtext('description', '')
            pub_date = item.findtext('pubDate', '')

            # Check if article is too old
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
    pattern = r'\b([A-Z]{3})/([A-Z]{3})\b'
    matches = re.findall(pattern, text)
    return matches


def determine_primary_currency_from_pair(text, base, quote):
    """
    Determine which currency in a pair is the primary focus of the article.

    Logic:
    - Check for directional words (rises, falls, strengthens, weakens, etc.)
    - The currency that appears with action verbs is typically the focus
    - In "GBP/USD rises", GBP is the focus (base currency strengthening)
    - In "USD weakens against EUR", USD is the focus

    Returns: base currency code or quote currency code
    """
    text_lower = text.lower()

    # Action words that indicate currency movement
    rising_words = ['rises', 'rising', 'climbs', 'climbing', 'gains', 'gaining',
                    'strengthens', 'strengthening', 'rallies', 'rallying', 'surges', 'surging',
                    'jumps', 'jumping', 'advances', 'advancing', 'higher', 'up']
    falling_words = ['falls', 'falling', 'drops', 'dropping', 'declines', 'declining',
                     'weakens', 'weakening', 'slumps', 'slumping', 'tumbles', 'tumbling',
                     'sinks', 'sinking', 'lower', 'down']

    # Get currency names from keywords
    base_keywords = CURRENCY_KEYWORDS.get(base, [base.lower()])
    quote_keywords = CURRENCY_KEYWORDS.get(quote, [quote.lower()])

    # Count directional mentions for each currency
    base_mentions = 0
    quote_mentions = 0

    for keyword in base_keywords:
        # Check if base currency appears with action words
        for word in rising_words + falling_words:
            if f"{keyword} {word}" in text_lower or f"{word} {keyword}" in text_lower:
                base_mentions += 1

    for keyword in quote_keywords:
        # Check if quote currency appears with action words
        for word in rising_words + falling_words:
            if f"{keyword} {word}" in text_lower or f"{word} {keyword}" in text_lower:
                quote_mentions += 1

    # Default: if pair notation appears (e.g., "GBP/USD rises"), base currency is the focus
    # This is FX convention: when GBP/USD rises, GBP is getting stronger
    pair_notation = f"{base}/{quote}"
    if pair_notation in text:
        # Check what happens to the pair
        pair_idx = text.find(pair_notation)
        following_text = text[pair_idx:pair_idx+100].lower()

        has_rising = any(word in following_text for word in rising_words)
        has_falling = any(word in following_text for word in falling_words)

        # If pair is rising/falling, base currency is the focus
        if has_rising or has_falling:
            return base

    # If one currency is mentioned more with action words, it's the focus
    if base_mentions > quote_mentions:
        return base
    elif quote_mentions > base_mentions:
        return quote

    # Default to base currency (FX convention)
    return base


def filter_articles_by_currency(articles, currency, min_score=0.3):
    """
    Filter articles relevant to a specific currency

    Enhanced logic:
    1. For articles with FX pair mentions, determine the PRIMARY currency focus
    2. Only assign article to the primary currency to avoid duplicates
    3. Fall back to keyword-based filtering for non-pair articles
    """
    relevant = []
    for article in articles:
        text = f"{article['title']} {article['snippet']}"

        # Check for FX pair mentions first
        pairs = detect_fx_pair_in_text(text)

        if pairs:
            # Article mentions FX pairs - determine primary focus
            for base, quote in pairs:
                if currency in (base, quote):
                    # This currency is in the pair - but is it the focus?
                    primary = determine_primary_currency_from_pair(text, base, quote)

                    if primary == currency:
                        # This currency is the PRIMARY focus
                        article_copy = article.copy()
                        article_copy['currency'] = currency
                        relevant.append(article_copy)
                        break  # Only add once per article
        else:
            # No FX pairs mentioned - use keyword-based relevance
            score = calculate_relevance(text, currency)
            if score >= min_score:
                article_copy = article.copy()
                article_copy['currency'] = currency
                relevant.append(article_copy)

    return relevant


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
            # Check if article is too old
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


def load_existing_urls(lookback_days=30):
    """
    Load all article URLs from existing news CSV files (past N days).

    This prevents re-downloading and re-analyzing articles that were
    already fetched in previous runs.

    Args:
        lookback_days: Number of days to look back (default: 30)

    Returns:
        Set of URLs from all existing news files
    """
    existing_urls = set()

    # Find all news CSV files
    news_files = sorted(glob.glob('/workspace/group/fx-portfolio/data/news/*.csv'))

    if not news_files:
        print("   No existing news files found")
        return existing_urls

    # Calculate cutoff date
    cutoff_date = datetime.now() - timedelta(days=lookback_days)
    cutoff_str = cutoff_date.strftime('%Y-%m-%d')

    # Load URLs from each file
    loaded_files = 0
    for filepath in news_files:
        # Extract date from filename
        filename = os.path.basename(filepath)
        file_date = filename.replace('.csv', '')

        # Skip files older than cutoff
        if file_date < cutoff_str:
            continue

        try:
            rows = read_csv('3', date=file_date, validate=False)
            urls_from_file = {row['url'] for row in rows}
            existing_urls.update(urls_from_file)
            loaded_files += 1
        except Exception as e:
            print(f"   ⚠️ Error reading {filepath}: {e}")

    print(f"   ✓ Loaded {len(existing_urls)} existing URLs from {loaded_files} files (past {lookback_days} days)")
    return existing_urls


def main(date_str=None):
    """Main aggregation function"""

    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    logger = PipelineLogger('step3', 'Fetch News Articles')
    logger.start()

    try:
        print("="*60)
        print("FX News Aggregator - CSV Output")
        print("="*60)
        print(f"\nProcessing date: {date_str}")

        # Load existing URLs from past 30 days to prevent re-downloading
        print(f"\n1. Loading existing article URLs (deduplication)...")
        existing_urls = load_existing_urls(lookback_days=30)
        logger.add_count('existing_urls_loaded', len(existing_urls))

        # Load sources
        sources_path = '/workspace/group/fx-portfolio/config/news_sources.json'
        with open(sources_path) as f:
            sources = json.load(f)

        all_articles = []

        # Fetch RSS feeds
        print(f"\n2. Fetching RSS feeds ({len(sources['rss_feeds'])} sources)...")
        for url in sources['rss_feeds']:
            print(f"   Fetching: {url}")

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
                print(f"   ✓ Found {len(articles)} articles (within 30 days)")

        logger.add_count('rss_articles_fetched', len(all_articles))

        # Fetch Reddit RSS (if any configured)
        reddit_urls = sources.get('reddit_rss', [])
        if reddit_urls:
            print(f"\n3. Fetching Reddit RSS ({len(reddit_urls)} sources)...")
            reddit_count = 0
            for url in reddit_urls:
                print(f"   Fetching: {url}")
                xml = fetch_rss(url)
                if xml:
                    articles = parse_rss(xml, source_name='Reddit')
                    all_articles.extend(articles)
                    reddit_count += len(articles)
                    print(f"   ✓ Found {len(articles)} posts (within 30 days)")
            logger.add_count('reddit_articles_fetched', reddit_count)

        # Fetch from NewsAPI (if enabled)
        if sources.get('newsapi_enabled', False):
            print(f"\n4. Fetching from NewsAPI.org...")

            queries = sources.get('newsapi_queries', ['forex'])
            max_per_query = sources.get('newsapi_max_results_per_query', 20)

            total_newsapi_count = 0
            for query in queries:
                print(f"   Query: '{query}'")
                newsapi_articles = fetch_from_newsapi(query, max_results=max_per_query)
                all_articles.extend(newsapi_articles)
                total_newsapi_count += len(newsapi_articles)

            print(f"   Total from NewsAPI: {total_newsapi_count} articles")
            print(f"   API requests used: {len(queries)} of 100/day limit")
            logger.add_count('newsapi_articles_fetched', total_newsapi_count)

        print(f"\n{'='*60}")
        print(f"Total articles fetched: {len(all_articles)}")
        print(f"{'='*60}\n")

        # Filter by currency and build CSV rows
        print(f"5. Filtering articles by currency ({len(CURRENCIES)} currencies)...")
        print(f"   Deduplicating against {len(existing_urls)} existing URLs...")

        csv_rows = []
        seen_urls = existing_urls.copy()  # Start with existing URLs from past 30 days
        new_urls_count = 0
        duplicate_urls_count = 0

        for currency in CURRENCIES:
            relevant = filter_articles_by_currency(all_articles, currency)

            # Add to CSV rows (deduplicate by URL against existing + current session)
            new_count = 0
            for article in relevant:
                url = article['url']
                if url not in seen_urls:
                    csv_rows.append({
                        'date': date_str,
                        'article_id': generate_article_id(url),
                        'source': article['source'],
                        'url': url,
                        'currency': currency,
                        'title': article['title'],
                        'snippet': article['snippet']
                    })
                    seen_urls.add(url)
                    new_count += 1
                    new_urls_count += 1
                else:
                    duplicate_urls_count += 1

            print(f"   {currency}: {new_count} new articles (skipped {len(relevant) - new_count} duplicates)")

        logger.add_count('unique_articles', len(csv_rows))
        logger.add_count('new_urls', new_urls_count)
        logger.add_count('duplicate_urls_skipped', duplicate_urls_count)

        print(f"\n{'='*60}")
        print(f"Deduplication Summary:")
        print(f"  New URLs: {new_urls_count}")
        print(f"  Duplicates skipped: {duplicate_urls_count}")
        print(f"  Total to save: {len(csv_rows)}")
        print(f"{'='*60}\n")

        # Write to CSV (always create file, even if empty)
        # This allows downstream processes to run correctly
        print(f"6. Saving to CSV...")
        csv_path = write_csv(csv_rows, 'process_3_news', date=date_str)
        if csv_rows:
            print(f"   ✓ Saved {len(csv_rows)} articles to {csv_path}")
        else:
            print(f"   ✓ Saved empty CSV (0 articles) to {csv_path}")
            logger.warning("No articles fetched - empty CSV created for downstream processes")
        logger.add_info('output_file', str(csv_path))

        logger.success()

        print(f"\n{'='*60}")
        print("✓ News aggregation complete")
        print(f"{'='*60}")

    except Exception as e:
        logger.error(f"Failed to fetch news: {e}")
        logger.fail()
        raise
    finally:
        logger.finish()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fetch news articles for currency analysis')
    parser.add_argument('--date', type=str, help='Date to process (YYYY-MM-DD), defaults to today')
    args = parser.parse_args()

    main(date_str=args.date)
