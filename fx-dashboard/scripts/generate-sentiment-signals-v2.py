#!/usr/bin/env python3
"""
Modular Sentiment Signal Generator for FX Portfolio
Supports multiple generator types configured in system_config.json
"""

import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime

sys.path.append('/workspace/group/fx-portfolio/scripts')
from pipeline_logger import PipelineLogger
from env_loader import get_anthropic_key

# Import keyword-based generator functions from original script
sys.path.append('/workspace/group/fx-portfolio/scripts')


def load_config():
    """Load system configuration"""
    config_path = '/workspace/group/fx-portfolio/config/system_config.json'
    with open(config_path, 'r') as f:
        return json.load(f)


def analyze_sentiment_keywords(combined_text, currency, params):
    """
    Keyword-based sentiment analysis (from original script)

    Args:
        combined_text: Article title + snippet
        currency: 3-letter currency code
        params: Generator parameters

    Returns:
        tuple: (direction, confidence, reasoning, magnitude)
    """
    import re

    text_lower = combined_text.lower()

    # Expanded sentiment keywords
    bullish_keywords = [
        # Original
        'gains', 'rises', 'climbs', 'strengthens', 'support', 'higher',
        'advances', 'rallies', 'upbeat', 'optimistic', 'hawkish', 'rate hike',
        'boost', 'positive', 'firm', 'strong', 'extends gains',
        # New - Strong positive
        'surges', 'soars', 'jumps', 'spikes', 'outperforms',
        'builds on gains', 'extends rally',
        # New - Support/momentum
        'supported by', 'underpinned by', 'bolstered by', 'lifted by',
        'boosted by', 'resilient', 'robust', 'buoyant',
        # New - Strength indicators
        'gains ground', 'picks up', 'bounces', 'rebounds'
    ]

    bearish_keywords = [
        # Original
        'falls', 'declines', 'tumbles', 'weakens', 'pressure', 'lower',
        'drops', 'slides', 'downbeat', 'pessimistic', 'dovish', 'rate cut',
        'drag', 'negative', 'soft', 'weak', 'loses ground', 'under pressure',
        # New - Strong negative
        'shudders', 'plunges', 'plummets', 'crashes', 'collapses',
        'slumps', 'sinks', 'dives', 'tumbled', 'erodes', 'deteriorates',
        # New - Negative movement
        'shedding', 'dropping', 'slipping', 'sliding', 'easing',
        'retreats', 'pulls back', 'pullback', 'gives up',
        # New - Negative impact
        'weighed on', 'weighs on', 'caps', 'pressures', 'pressured',
        'dented', 'hurt', 'dragged down', 'struck down', 'blocks',
        'trimmed', 'pared', 'reversed',
        # New - Uncertainty/weakness
        'uncertainty', 'concerns', 'worries', 'risks', 'headwinds',
        'falters', 'stumbles', 'struggles', 'subdued', 'muted'
    ]

    neutral_keywords = [
        'stable', 'steady', 'unchanged', 'flat', 'consolidates',
        'little changed', 'holds ground', 'mixed', 'choppy',
        'sideways', 'rangebound', 'hovers'
    ]

    # Negation patterns
    negation_patterns = [
        r'shed(?:s|ding)?\s+(?:early[- ]session\s+)?gains?',
        r'trim(?:s|med|ming)?\s+gains?',
        r'pare(?:s|d|ing)?\s+gains?',
        r'give(?:s|ing)?\s+up\s+gains?',
        r'revers(?:e|es|ed|ing)\s+gains?',
        r'erase(?:s|d|ing)?\s+gains?',
        r'lose(?:s|ing)?\s+gains?',
        r'give(?:s|n)?\s+(?:back|away)\s+gains?'
    ]

    # Check for negation patterns
    has_negation = False
    if params.get('negation_enabled', True):
        for pattern in negation_patterns:
            if re.search(pattern, text_lower):
                has_negation = True
                break

    # Count keywords
    bullish_count = sum(1 for kw in bullish_keywords if kw in text_lower)
    bearish_count = sum(1 for kw in bearish_keywords if kw in text_lower)
    neutral_count = sum(1 for kw in neutral_keywords if kw in text_lower)

    # Apply negation
    if has_negation and bullish_count > 0:
        bearish_count += bullish_count
        bullish_count = 0

    # Determine direction and confidence
    min_count = params.get('min_keyword_count', 1)
    total_keywords = bullish_count + bearish_count + neutral_count

    if bullish_count >= min_count and bullish_count > bearish_count:
        direction = 'bullish'
        confidence = min(0.9, (bullish_count / max(1, total_keywords)) * params.get('confidence_boost', 1.5))
        reasoning = f"{currency} showing strength with {bullish_count} positive indicators"
        magnitude = 'small' if bullish_count <= 2 else 'medium' if bullish_count <= 4 else 'large'
    elif bearish_count >= min_count and bearish_count > bullish_count:
        direction = 'bearish'
        confidence = min(0.9, (bearish_count / max(1, total_keywords)) * params.get('confidence_boost', 1.5))
        reasoning = f"{currency} showing weakness with {bearish_count} negative indicators"
        magnitude = 'small' if bearish_count <= 2 else 'medium' if bearish_count <= 4 else 'large'
    else:
        direction = 'neutral'
        confidence = 0.3
        reasoning = f"{currency} mixed signals; markets consolidating"
        magnitude = None

    return direction, round(confidence, 2), reasoning, magnitude


def analyze_sentiment_llm(combined_text, currency, params):
    """
    LLM-based sentiment analysis using Claude Haiku

    Args:
        combined_text: Article title + snippet
        currency: 3-letter currency code
        params: Generator parameters (model, temperature, etc.)

    Returns:
        tuple: (direction, confidence, reasoning, magnitude)
    """
    api_key = get_anthropic_key()
    if not api_key:
        print("  ⚠️  Anthropic API key not found, falling back to neutral")
        return 'neutral', 0.3, 'API key not available', None

    # Build prompt
    prompt = f"""You are an expert FX market analyst. Analyze this news article and determine its sentiment for {currency}.

**Article Text**:
{combined_text}

**Your task**: Determine the sentiment for {currency} based on this article.

**Analysis Framework**:
1. **Direction**: Is this BULLISH (positive for {currency}), BEARISH (negative for {currency}), or NEUTRAL?
2. **Confidence**: How confident are you? (0.0 = not confident, 1.0 = very confident)
3. **Magnitude**: If directional, is the expected impact SMALL, MEDIUM, or LARGE?
4. **Reasoning**: Brief explanation (1-2 sentences)

**Important Considerations**:
- FX pairs: If article mentions "{currency}/XXX rises", that's BULLISH for {currency}
- FX pairs: If article mentions "XXX/{currency} rises", that's BEARISH for {currency} (inverse)
- Central bank hawkishness → BULLISH for currency
- Central bank dovishness → BEARISH for currency
- Economic strength indicators → BULLISH
- Economic weakness indicators → BEARISH

**Output Format (JSON)**:
{{
  "direction": "bullish|bearish|neutral",
  "confidence": 0.0-1.0,
  "magnitude": "small|medium|large|null",
  "reasoning": "brief explanation"
}}

Return ONLY the JSON, no other text."""

    # Call Anthropic API
    try:
        url = "https://api.anthropic.com/v1/messages"
        request_body = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 300,
            "temperature": params.get('temperature', 0.3),
            "messages": [{"role": "user", "content": prompt}]
        }

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(request_body).encode('utf-8'),
            headers=headers
        )

        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            response_text = result['content'][0]['text']

            # Extract JSON from response (handle markdown code blocks)
            import re
            json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group(0))

                direction = analysis.get('direction', 'neutral')
                confidence = float(analysis.get('confidence', 0.5))
                magnitude = analysis.get('magnitude')
                reasoning = analysis.get('reasoning', 'LLM analysis')

                return direction, round(confidence, 2), reasoning, magnitude
            else:
                print(f"  ⚠️  Failed to parse LLM response, falling back to neutral")
                return 'neutral', 0.3, 'Parse error', None

    except Exception as e:
        print(f"  ⚠️  LLM API error: {str(e)[:100]}, falling back to neutral")
        return 'neutral', 0.3, f'API error: {str(e)[:50]}', None


def detect_fx_pair(title):
    """Detect FX pair mentions in title (e.g., "AUD/USD", "EUR/GBP")"""
    import re
    pattern = r'\b([A-Z]{3})/([A-Z]{3})\b'
    match = re.search(pattern, title)
    if match:
        return match.group(1), match.group(2)
    return None, None


def invert_direction(direction):
    """Invert bullish/bearish for counter-currency"""
    if direction == 'bullish':
        return 'bearish'
    elif direction == 'bearish':
        return 'bullish'
    else:
        return 'neutral'


def generate_signals_for_currency_and_generator(currency, generator_config, date_str=None):
    """
    Generate sentiment signals for a currency using a specific generator

    Args:
        currency: 3-letter currency code
        generator_config: Generator configuration from system_config.json
        date_str: Date string (YYYY-MM-DD), defaults to today

    Returns:
        list: Signal objects
    """
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    # Read news data
    news_file = f'/workspace/group/fx-portfolio/data/news/{currency}/{date_str}.json'

    if not os.path.exists(news_file):
        return []

    with open(news_file, 'r') as f:
        news_data = json.load(f)

    articles = news_data.get('articles', [])
    if not articles:
        return []

    signals = []
    generator_id = generator_config['id']
    generator_type = generator_config['type']
    generator_params = generator_config.get('params', {})

    # Select analysis function based on generator type
    if generator_type == 'keyword-sentiment-v1.1':
        analyze_func = analyze_sentiment_keywords
    elif generator_type == 'llm-sentiment-v1':
        analyze_func = analyze_sentiment_llm
    else:
        print(f"  ⚠️  Unknown generator type: {generator_type}")
        return []

    # Generate signal per article
    for article in articles:
        title = article.get('title', '')
        article_text = f"{title} {article.get('snippet', '')}"

        # Analyze sentiment
        direction, confidence, reasoning, predicted_magnitude = analyze_func(
            article_text, currency, generator_params
        )

        # Check for FX pair mentions
        base_curr, quote_curr = detect_fx_pair(title)
        signal_direction = direction
        pair_context = None

        if base_curr and quote_curr:
            pair_context = f"{base_curr}/{quote_curr}"

            if currency == base_curr:
                signal_direction = direction
                reasoning = f"{pair_context}: {reasoning}"
            elif currency == quote_curr:
                signal_direction = invert_direction(direction)
                reasoning = f"{pair_context}: Inverse signal for quote currency - {reasoning}"

        # Build signal
        signal = {
            "date": date_str,
            "generator_id": generator_id,
            "generator_type": generator_type,
            "generator_params": generator_params,
            "signal_type": "news-sentiment",
            "currency": currency,
            "predicted_direction": signal_direction,
            "predicted_magnitude": predicted_magnitude if predicted_magnitude else None,
            "confidence": round(confidence, 4) if confidence is not None else None,
            "pair_context": pair_context,
            "article_url": article.get('url'),
            "article_title": title,
            "published_at": article.get('published_at'),
            "relevance_score": round(article.get('relevance_score', 0), 4) if article.get('relevance_score') else None,
            "reasoning": reasoning if reasoning else None,
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }

        signals.append(signal)

    return signals


def main():
    """Generate sentiment signals using all configured generators"""
    import argparse

    parser = argparse.ArgumentParser(description='Generate sentiment signals from news')
    parser.add_argument('--date', help='Date to process (YYYY-MM-DD). If not specified, uses most recent.')
    args = parser.parse_args()

    logger = PipelineLogger('step5', 'Generate Sentiment Signals (v2)')
    logger.start()

    # Load configuration
    config = load_config()
    currencies = config['currencies']
    signal_generators = config['signal_generators']

    print(f"Loaded {len(signal_generators)} signal generators:")
    for gen_id, gen_config in signal_generators.items():
        print(f"  - {gen_id} ({gen_config['type']}): {gen_config.get('description', 'N/A')}")

    logger.add_count('generators_configured', len(signal_generators))
    logger.add_count('currencies_to_analyze', len(currencies))

    # Determine date to process
    if args.date:
        date_str = args.date
        print(f"\nProcessing date: {date_str}")

        # Validate news data exists for this date
        news_dir = '/workspace/group/fx-portfolio/data/news/USD'
        news_file = f'{news_dir}/{date_str}.json'
        if not os.path.exists(news_file):
            print(f"❌ No news data found for {date_str}")
            print(f"   Step 3 (News Aggregation) must be run first for this date")
            logger.error("Missing upstream data", {"step": 3, "date": date_str})
            logger.finish()
            return
    else:
        # Find most recent news date
        date_str = datetime.now().strftime('%Y-%m-%d')
        news_dir = '/workspace/group/fx-portfolio/data/news/USD'
        if os.path.exists(news_dir):
            news_files = sorted([f for f in os.listdir(news_dir) if f.endswith('.json')])
            if news_files:
                date_str = news_files[-1].replace('.json', '')
                print(f"\nUsing most recent news date: {date_str}")

    all_signals = []
    summary_by_generator = {}

    try:
        # Loop through each generator
        for gen_id, gen_config in signal_generators.items():
            print(f"\n{'='*60}")
            print(f"Generator: {gen_id}")
            print(f"Type: {gen_config['type']}")
            print(f"{'='*60}")

            generator_signals = []

            # Generate signals for each currency
            for currency in currencies:
                print(f"\nAnalyzing {currency} with {gen_id}...")
                signals = generate_signals_for_currency_and_generator(
                    currency, gen_config, date_str
                )

                if signals:
                    generator_signals.extend(signals)
                    print(f"  ✓ Generated {len(signals)} signals")

            # Save signals for this generator
            if generator_signals:
                # Group by currency
                signals_by_currency = {}
                for signal in generator_signals:
                    curr = signal['currency']
                    if curr not in signals_by_currency:
                        signals_by_currency[curr] = []
                    signals_by_currency[curr].append(signal)

                # Save to files (one file per currency)
                for currency, curr_signals in signals_by_currency.items():
                    output_dir = f'/workspace/group/fx-portfolio/data/signals/{currency}'
                    os.makedirs(output_dir, exist_ok=True)
                    filepath = f'{output_dir}/{date_str}.json'

                    # Read existing signals if file exists
                    existing_signals = []
                    if os.path.exists(filepath):
                        with open(filepath, 'r') as f:
                            existing_data = json.load(f)
                            existing_signals = existing_data.get('signals', [])

                    # Deduplicate: remove existing signals for same generator+article
                    # Unique key: (generator_id, article_url)
                    new_signal_keys = {(s['generator_id'], s['article_url']) for s in curr_signals}
                    deduplicated_existing = [
                        s for s in existing_signals
                        if (s['generator_id'], s['article_url']) not in new_signal_keys
                    ]

                    # Append new signals to deduplicated existing
                    all_currency_signals = deduplicated_existing + curr_signals

                    # Save
                    output_data = {
                        'currency': currency,
                        'date': date_str,
                        'signals': all_currency_signals
                    }

                    with open(filepath, 'w') as f:
                        json.dump(output_data, f, indent=2)

                all_signals.extend(generator_signals)

                # Calculate summary
                bullish = sum(1 for s in generator_signals if s['predicted_direction'] == 'bullish')
                bearish = sum(1 for s in generator_signals if s['predicted_direction'] == 'bearish')
                neutral = sum(1 for s in generator_signals if s['predicted_direction'] == 'neutral')
                avg_conf = sum(s['confidence'] for s in generator_signals if s['confidence']) / len(generator_signals) if generator_signals else 0

                summary_by_generator[gen_id] = {
                    'total': len(generator_signals),
                    'bullish': bullish,
                    'bearish': bearish,
                    'neutral': neutral,
                    'avg_confidence': avg_conf
                }

                print(f"\n✓ Generator {gen_id}: {len(generator_signals)} total signals")
                print(f"  Bullish: {bullish}, Bearish: {bearish}, Neutral: {neutral}")
                print(f"  Avg confidence: {avg_conf:.2f}")

        logger.add_count('total_signals', len(all_signals))
        logger.add_count('generators_executed', len(summary_by_generator))

        print(f"\n{'='*60}")
        print(f"✓ Generated {len(all_signals)} total signals from {len(summary_by_generator)} generators")
        print(f"{'='*60}")

        # Summary table
        if summary_by_generator:
            print("\nGenerator Summary:")
            print(f"{'Generator':<50} {'Total':<8} {'Bull':<6} {'Bear':<6} {'Neut':<6} {'Conf':<6}")
            print("-" * 82)
            for gen_id, stats in summary_by_generator.items():
                print(f"{gen_id:<50} {stats['total']:<8} {stats['bullish']:<6} {stats['bearish']:<6} {stats['neutral']:<6} {stats['avg_confidence']:<6.2f}")

        logger.finish()

        print(f"\n{'='*60}")

    except Exception as e:
        logger.add_error(f"Error in signal generation: {str(e)}")
        logger.finish()
        raise


if __name__ == '__main__':
    main()
