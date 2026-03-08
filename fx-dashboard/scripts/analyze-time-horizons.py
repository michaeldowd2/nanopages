#!/usr/bin/env python3
"""
Time Horizon Analysis with LLM
Analyzes news articles using Claude Haiku to estimate time horizons
"""

import json
import os
import sys
import hashlib
import urllib.request
import urllib.parse
import argparse
from datetime import datetime
from pathlib import Path

# Add scripts directory to path
sys.path.append(os.path.dirname(__file__))
from env_loader import get_anthropic_key
from pipeline_logger import PipelineLogger
from config_loader import get_estimators

# Time horizon categories
TIME_HORIZONS = {
    '1day': {'days': 1, 'description': 'Immediate/Intraday (same day impact)'},
    '3day': {'days': 3, 'description': 'Short-term (2-3 days)'},
    '1week': {'days': 7, 'description': 'Near-term (1 week)'},
    '2week': {'days': 14, 'description': 'Medium-term (2 weeks)'},
    '1month': {'days': 30, 'description': 'Longer-term (up to 1 month)'}
}

# Load estimator configuration from system_config.json
estimators = get_estimators()
if not estimators:
    print("ERROR: No horizon estimators found in system_config.json")
    sys.exit(1)

# Use the first (and currently only) estimator
estimator_config = list(estimators.values())[0]
ESTIMATOR_ID = estimator_config['id']
ESTIMATOR_TYPE = estimator_config['type']
ESTIMATOR_PARAMS = estimator_config.get('params', {})

# LLM Prompt for horizon analysis
HORIZON_ANALYSIS_PROMPT = """You are an expert FX market analyst. Analyze the following news article and estimate its TIME HORIZON - how long the market impact or relevance will last.

**Article Title**: {title}

**Article Snippet**: {snippet}

**Currency**: {currency}

**Date Retrieved**: {date}

---

**Your task**: Estimate the time horizon by analyzing:

1. **Event Type Indicators**:
   - IMMEDIATE (1day): Intraday moves, immediate reactions, "today", "now", breaking news, flash data
   - SHORT-TERM (3day): "this week", GDP releases, employment data, inflation reports
   - NEAR-TERM (1week): Central bank meetings, policy decisions, "next week"
   - MEDIUM-TERM (2week): Trade negotiations, geopolitical developments, "coming weeks"
   - LONGER-TERM (1month): Structural changes, regulatory shifts, "next month", trends

2. **Market Impact Patterns**:
   - Price action mentions (immediate)
   - Economic data releases (3day to 1week)
   - Central bank policy (1week to 2week)
   - Geopolitical events (2week to 1month)
   - Structural trends (1month)

3. **Temporal Keywords**:
   - "Intraday", "today", "session" → 1day
   - "This week", "upcoming" → 3day
   - "Next week", "near-term" → 1week
   - "Coming weeks", "medium-term" → 2week
   - "Next month", "longer-term", "trend" → 1month

4. **Data Release Types**:
   - Flash PMI, intraday comments → 1day
   - Monthly CPI, NFP, GDP → 3day to 1week
   - FOMC/ECB meetings → 1week to 2week
   - Trade deals, policy changes → 2week to 1month

---

**Available Horizons**:
- 1day: Immediate/Intraday impact (same day)
- 3day: Short-term (2-3 days)
- 1week: Near-term (1 week)
- 2week: Medium-term (2 weeks)
- 1month: Longer-term (up to 1 month)

**Output Format** (JSON only, no explanation):
{{
  "time_horizon": "<one of: 1day|3day|1week|2week|1month>",
  "confidence": <0.0-1.0>,
  "reasoning": "<brief explanation in 1-2 sentences>"
}}

**Important**:
- Choose ONE horizon that best fits
- Be conservative - if uncertain between two, choose the shorter one
- Focus on the PRIMARY market impact window
- Confidence should reflect certainty (0.8 is typical, use 0.9+ only for very clear cases)
"""


def analyze_article_horizon(article, api_key):
    """
    Use Claude Haiku to analyze an article's time horizon

    Returns: dict with time_horizon, confidence, reasoning
    """
    # Build prompt
    prompt = HORIZON_ANALYSIS_PROMPT.format(
        title=article['title'],
        snippet=article['snippet'],
        currency=article['currency'],
        date=article.get('date', 'unknown')
    )

    # Call Claude API
    request_data = {
        "model": ESTIMATOR_PARAMS['model'],
        "max_tokens": ESTIMATOR_PARAMS.get('max_tokens', 500),
        "temperature": ESTIMATOR_PARAMS.get('temperature', 0.3),
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=json.dumps(request_data).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01'
        }
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.loads(response.read().decode('utf-8'))

    # Extract JSON from response
    content = result['content'][0]['text'].strip()

    # Parse JSON (handle markdown code blocks)
    if '```json' in content:
        content = content.split('```json')[1].split('```')[0].strip()
    elif '```' in content:
        content = content.split('```')[1].split('```')[0].strip()

    analysis = json.loads(content)

    # Validate horizon
    if analysis['time_horizon'] not in TIME_HORIZONS:
        raise ValueError(f"Invalid time horizon: {analysis['time_horizon']}")

    # Add horizon_days (numeric days)
    analysis['horizon_days'] = TIME_HORIZONS[analysis['time_horizon']]['days']

    return analysis


def load_articles_for_date(date_str):
    """
    Load all articles from Step 3 (news) for a specific date.

    Parameters:
    - date_str: Date in YYYY-MM-DD format

    Returns: List of article dicts with url, title, snippet, currency, etc.
    """
    articles = []
    news_dir = Path('/workspace/group/fx-portfolio/data/news')

    # Check if news data exists for this date
    if not news_dir.exists():
        print(f"⚠️  News directory not found: {news_dir}")
        return articles

    # Iterate through currency directories
    for currency_dir in news_dir.iterdir():
        if not currency_dir.is_dir():
            continue

        currency = currency_dir.name
        date_file = currency_dir / f"{date_str}.json"

        if date_file.exists():
            with open(date_file) as f:
                data = json.load(f)

            # Verify this file is for the correct date
            if data.get('date') != date_str:
                continue

            # Add each article with metadata
            for article in data.get('articles', []):
                articles.append({
                    'url': article['url'],
                    'title': article['title'],
                    'snippet': article.get('snippet', ''),
                    'currency': currency,
                    'source': article.get('source', 'Unknown'),
                    'relevance_score': article.get('relevance_score', 0),
                    'date': date_str  # Data/retrieval date
                })

    return articles


def check_existing_analysis(date_str):
    """
    Check if analysis already exists for this date.
    Returns dict of url -> analysis data for existing analyses.
    """
    output_dir = Path('/workspace/group/fx-portfolio/data/article-analysis')
    output_file = output_dir / f"{date_str}.json"

    if output_file.exists():
        with open(output_file) as f:
            data = json.load(f)
            return {item['url']: item for item in data.get('analyses', [])}

    return {}


def save_analyses(date_str, analyses):
    """
    Save all analyses for a specific date to a JSON file.

    Parameters:
    - date_str: Date in YYYY-MM-DD format
    - analyses: List of analysis dicts
    """
    output_dir = Path('/workspace/group/fx-portfolio/data/article-analysis')
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{date_str}.json"

    output_data = {
        'date': date_str,
        'estimator_id': ESTIMATOR_ID,
        'estimator_type': ESTIMATOR_TYPE,
        'estimator_params': ESTIMATOR_PARAMS,
        'analyzed_at': datetime.now().isoformat(),
        'analyses': analyses
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"✓ Saved {len(analyses)} analyses to {output_file}")


def main():
    """Main function - analyze articles for a specific date"""
    parser = argparse.ArgumentParser(description='Analyze time horizons for news articles')
    parser.add_argument('--date', help='Date to process (YYYY-MM-DD). Required.')
    args = parser.parse_args()

    # Date is required
    if not args.date:
        print("❌ Error: --date parameter is required")
        print("   Usage: python3 analyze-time-horizons.py --date 2026-02-24")
        sys.exit(1)

    date_str = args.date

    logger = PipelineLogger("step4", "Analyze Time Horizons (LLM)")
    logger.start()

    print("="*60)
    print("Time Horizon Analysis with Claude Haiku")
    print("="*60)
    print(f"Processing date: {date_str}")

    # Get API key
    api_key = get_anthropic_key()
    if not api_key:
        print("\n❌ Anthropic API key not found!")
        print("   Set ANT_API_KEY in /workspace/project/.env")
        logger.error("Missing API key", {"message": "ANTHROPIC_API_KEY not found"})
        logger.finish()
        sys.exit(1)

    print(f"✓ API key loaded")

    # Validate upstream data exists (Step 3: News)
    articles = load_articles_for_date(date_str)

    if not articles:
        print(f"\n❌ No news articles found for {date_str}")
        print(f"   Step 3 (News Aggregation) must be run first for this date")
        logger.error("Missing upstream data", {
            "step": 3,
            "date": date_str,
            "message": "No news articles found"
        })
        logger.finish()
        sys.exit(1)

    print(f"✓ Found {len(articles)} articles from Step 3 for {date_str}")

    # Check for existing analyses
    existing_analyses = check_existing_analysis(date_str)

    if existing_analyses:
        print(f"⚠️  Found existing analysis for {date_str} with {len(existing_analyses)} articles")
        print(f"   Re-analyzing will overwrite existing data")

    # Filter articles that need analysis
    articles_to_analyze = [a for a in articles if a['url'] not in existing_analyses]

    if not articles_to_analyze:
        print(f"\n✓ All {len(articles)} articles already analyzed for {date_str}")
        logger.finish()
        return

    print(f"\n📊 Analyzing {len(articles_to_analyze)} new articles...")
    print(f"   Estimator: {ESTIMATOR_ID}")
    print(f"   Model: {ESTIMATOR_PARAMS['model']}")

    # Analyze each article
    horizon_counts = {h: 0 for h in TIME_HORIZONS.keys()}
    all_analyses = list(existing_analyses.values())  # Start with existing
    analyzed_count = 0
    failed_count = 0

    for i, article in enumerate(articles_to_analyze, 1):
        print(f"\n[{i}/{len(articles_to_analyze)}] {article['title'][:50]}...")
        print(f"   Currency: {article['currency']}, Source: {article.get('source', 'Unknown')}")

        try:
            # Analyze with LLM
            result = analyze_article_horizon(article, api_key)

            # Calculate valid_to_date (date + horizon_days)
            from datetime import datetime, timedelta
            date_obj = datetime.fromisoformat(date_str)
            valid_to_obj = date_obj + timedelta(days=result['horizon_days'])
            valid_to_date = valid_to_obj.strftime('%Y-%m-%d')

            # Build analysis record
            analysis_record = {
                'url': article['url'],
                'currency': article['currency'],
                'title': article['title'],
                'source': article['source'],
                'time_horizon': result['time_horizon'],
                'horizon_days': result['horizon_days'],
                'valid_to_date': valid_to_date,
                'confidence': result['confidence'],
                'reasoning': result['reasoning']
            }

            all_analyses.append(analysis_record)

            # Track stats
            horizon_counts[result['time_horizon']] += 1
            analyzed_count += 1

            print(f"   ✓ Horizon: {result['time_horizon']} (confidence: {result['confidence']:.2f})")
            print(f"     {result['reasoning'][:80]}...")

        except Exception as e:
            print(f"   ✗ Error: {e}")
            failed_count += 1
            logger.error(f"Analysis failed for article {i}: {article['url']} - {str(e)}")

    # Save all analyses for this date
    if analyzed_count > 0:
        save_analyses(date_str, all_analyses)

    # Summary
    print(f"\n{'='*60}")
    print("Analysis Complete")
    print(f"{'='*60}")
    print(f"✓ Analyzed: {analyzed_count} new articles")
    print(f"✓ Total for {date_str}: {len(all_analyses)} articles")
    if failed_count > 0:
        print(f"✗ Failed: {failed_count}")

    if analyzed_count > 0:
        print(f"\nHorizon Distribution (new analyses):")
        for horizon, count in sorted(horizon_counts.items(), key=lambda x: TIME_HORIZONS[x[0]]['days']):
            if count > 0:
                pct = 100 * count / analyzed_count if analyzed_count > 0 else 0
                print(f"  {horizon:8s} ({TIME_HORIZONS[horizon]['days']:2d} days): {count:3d} articles ({pct:5.1f}%)")

    logger.add_count('articles_analyzed', analyzed_count)
    logger.add_count('articles_failed', failed_count)
    logger.add_count('total_articles', len(all_analyses))
    logger.finish()

    print(f"\n{'='*60}")


if __name__ == '__main__':
    main()
