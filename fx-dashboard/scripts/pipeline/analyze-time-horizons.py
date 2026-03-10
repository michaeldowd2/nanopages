#!/usr/bin/env python3
"""
Step 4: Time Horizon Analysis with LLM

Analyzes news articles using Claude Haiku to estimate time horizons.
Reads from Process 3 CSV output, writes to Process 4 CSV output.

Input: data/news/{date}.csv (from Process 3)
Output: data/article-analysis/{date}.csv
"""

import json
import os
import sys
import urllib.request
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Add scripts directory to path
sys.path.append('/workspace/group/fx-portfolio/scripts')
from utilities.env_loader import get_anthropic_key
from utilities.pipeline_logger import PipelineLogger
from utilities.config_loader import get_estimators
from utilities.csv_helper import read_csv, write_csv

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


def main(date_str=None):
    """Main function - analyze articles for a specific date"""

    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    logger = PipelineLogger("step4", "Analyze Time Horizons (LLM)")
    logger.start()

    try:
        print("="*60)
        print("Time Horizon Analysis with Claude Haiku - CSV Output")
        print("="*60)
        print(f"\nProcessing date: {date_str}")

        # Get API key
        api_key = get_anthropic_key()
        if not api_key:
            print("\n❌ Anthropic API key not found!")
            print("   Set ANT_API_KEY in /workspace/project/.env")
            logger.error("Missing API key")
            logger.fail()
            return

        print(f"✓ API key loaded")

        # Load articles from Process 3 CSV
        print(f"\n1. Loading news articles from Process 3...")
        try:
            articles = read_csv('process_3_news', date=date_str, validate=False)
            print(f"   ✓ Loaded {len(articles)} articles")
            logger.add_count('articles_loaded', len(articles))
        except FileNotFoundError:
            print(f"   ✗ No news articles found for {date_str}")
            print(f"   Step 3 (News Aggregation) must be run first")
            logger.error(f"Missing upstream data: process_3_news for {date_str}")
            logger.fail()
            return

        if not articles:
            print(f"   ⚠ No articles to analyze")
            logger.warning("No articles found")
            logger.fail()
            return

        # Analyze each article
        print(f"\n2. Analyzing {len(articles)} articles with LLM...")
        print(f"   Estimator: {ESTIMATOR_ID}")
        print(f"   Model: {ESTIMATOR_PARAMS['model']}")

        csv_rows = []
        horizon_counts = {h: 0 for h in TIME_HORIZONS.keys()}
        analyzed_count = 0
        failed_count = 0

        for i, article in enumerate(articles, 1):
            print(f"\n   [{i}/{len(articles)}] {article['title'][:60]}...")
            print(f"      Currency: {article['currency']}, Source: {article.get('source', 'Unknown')}")

            try:
                # Analyze with LLM
                result = analyze_article_horizon(article, api_key)

                # Calculate valid_to_date (date + horizon_days)
                date_obj = datetime.fromisoformat(date_str)
                valid_to_obj = date_obj + timedelta(days=result['horizon_days'])
                valid_to_date = valid_to_obj.strftime('%Y-%m-%d')

                # Build CSV row
                csv_rows.append({
                    'date': date_str,
                    'source': article['source'],
                    'url': article['url'],
                    'currency': article['currency'],
                    'title': article['title'],
                    'estimator_id': ESTIMATOR_ID,
                    'time_horizon': result['time_horizon'],
                    'horizon_days': result['horizon_days'],
                    'valid_to_date': valid_to_date,
                    'confidence': result['confidence'],
                    'reasoning': result['reasoning']
                })

                # Track stats
                horizon_counts[result['time_horizon']] += 1
                analyzed_count += 1

                print(f"      ✓ Horizon: {result['time_horizon']} (confidence: {result['confidence']:.2f})")

            except Exception as e:
                print(f"      ✗ Error: {e}")
                failed_count += 1
                logger.warning(f"Analysis failed for article: {article['url']} - {str(e)}")

        logger.add_count('articles_analyzed', analyzed_count)
        logger.add_count('articles_failed', failed_count)

        # Write to CSV
        print(f"\n3. Saving to CSV...")
        if csv_rows:
            csv_path = write_csv(csv_rows, 'process_4_horizons', date=date_str)
            print(f"   ✓ Saved {len(csv_rows)} analyses to {csv_path}")
            logger.add_info('output_file', str(csv_path))
        else:
            print(f"   ⚠ No analyses to save")
            logger.warning("No successful analyses")

        # Summary
        print(f"\n{'='*60}")
        print("Analysis Complete")
        print(f"{'='*60}")
        print(f"✓ Analyzed: {analyzed_count} articles")
        if failed_count > 0:
            print(f"✗ Failed: {failed_count}")

        if analyzed_count > 0:
            print(f"\nHorizon Distribution:")
            for horizon, count in sorted(horizon_counts.items(), key=lambda x: TIME_HORIZONS[x[0]]['days']):
                if count > 0:
                    pct = 100 * count / analyzed_count if analyzed_count > 0 else 0
                    print(f"  {horizon:8s} ({TIME_HORIZONS[horizon]['days']:2d} days): {count:3d} articles ({pct:5.1f}%)")

        logger.success()

    except Exception as e:
        logger.error(f"Failed to analyze time horizons: {e}")
        logger.fail()
        raise
    finally:
        logger.finish()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze time horizons for news articles')
    parser.add_argument('--date', type=str, help='Date to process (YYYY-MM-DD), defaults to today')
    args = parser.parse_args()

    main(date_str=args.date)
