#!/usr/bin/env python3
"""
Step 5: Modular Sentiment Signal Generator for FX Portfolio

Supports multiple generator types configured in system_config.json.
Reads from Process 3 CSV output, writes to Process 5 CSV output.

Input: data/news/{date}.csv (from Process 3)
Output: data/signals/{date}.csv
"""

import json
import os
import sys
import urllib.request
import argparse
from datetime import datetime

sys.path.append('/workspace/group/fx-portfolio/scripts')
from utilities.pipeline_logger import PipelineLogger
from utilities.env_loader import get_anthropic_key
from utilities.csv_helper import read_csv, write_csv


def load_config():
    """Load system configuration"""
    config_path = '/workspace/group/fx-portfolio/config/system_config.json'
    with open(config_path, 'r') as f:
        return json.load(f)


def analyze_sentiment_keywords(combined_text, currency, params):
    """
    Keyword-based sentiment analysis

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
        'gains', 'rises', 'climbs', 'strengthens', 'support', 'higher',
        'advances', 'rallies', 'upbeat', 'optimistic', 'hawkish', 'rate hike',
        'boost', 'positive', 'firm', 'strong', 'extends gains',
        'surges', 'soars', 'jumps', 'spikes', 'outperforms',
        'builds on gains', 'extends rally',
        'supported by', 'underpinned by', 'bolstered by', 'lifted by',
        'boosted by', 'resilient', 'robust', 'buoyant',
        'gains ground', 'picks up', 'bounces', 'rebounds'
    ]

    bearish_keywords = [
        'falls', 'declines', 'tumbles', 'weakens', 'pressure', 'lower',
        'drops', 'slides', 'downbeat', 'pessimistic', 'dovish', 'rate cut',
        'drag', 'negative', 'soft', 'weak', 'loses ground', 'under pressure',
        'shudders', 'plunges', 'plummets', 'crashes', 'collapses',
        'slumps', 'sinks', 'dives', 'tumbled', 'erodes', 'deteriorates',
        'shedding', 'dropping', 'slipping', 'sliding', 'easing',
        'retreats', 'pulls back', 'pullback', 'gives up',
        'weighed on', 'weighs on', 'caps', 'pressures', 'pressured',
        'dented', 'hurt', 'dragged down', 'struck down', 'blocks',
        'trimmed', 'pared', 'reversed',
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


def main(date_str=None):
    """Generate sentiment signals using all configured generators"""

    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    logger = PipelineLogger('step5', 'Generate Sentiment Signals (CSV)')
    logger.start()

    try:
        print("="*60)
        print("Sentiment Signal Generator - CSV Output")
        print("="*60)
        print(f"\nProcessing date: {date_str}")

        # Load configuration
        config = load_config()
        signal_generators = config['signal_generators']

        print(f"\n✓ Loaded {len(signal_generators)} signal generators:")
        for gen_id, gen_config in signal_generators.items():
            print(f"  - {gen_id} ({gen_config['type']})")

        logger.add_count('generators_configured', len(signal_generators))

        # Load news articles from Process 3 CSV
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

        # Load horizon analyses from Process 4 CSV
        print(f"\n2. Loading horizon analyses from Process 4...")
        try:
            horizons = read_csv('process_4_horizons', date=date_str, validate=False)
            print(f"   ✓ Loaded {len(horizons)} horizon analyses")
            logger.add_count('horizons_loaded', len(horizons))
        except FileNotFoundError:
            print(f"   ✗ No horizon analyses found for {date_str}")
            print(f"   Step 4 (Time Horizon Analysis) must be run first")
            logger.error(f"Missing upstream data: process_4_horizons for {date_str}")
            logger.fail()
            return

        # Create horizon lookup by (article_id, currency)
        horizon_lookup = {}
        for h in horizons:
            key = (h['article_id'], h['currency'])
            horizon_lookup[key] = h

        if not articles:
            print(f"   ⚠ No articles to analyze")
            logger.warning("No articles found")
            logger.fail()
            return

        # Generate signals with each generator
        all_signals = []
        summary_by_generator = {}

        for gen_id, gen_config in signal_generators.items():
            print(f"\n{'='*60}")
            print(f"Generator: {gen_id}")
            print(f"Type: {gen_config['type']}")
            print(f"{'='*60}")

            generator_type = gen_config['type']
            generator_params = gen_config.get('params', {})

            # Select analysis function
            if generator_type == 'keyword-sentiment-v1.1':
                analyze_func = analyze_sentiment_keywords
            elif generator_type == 'llm-sentiment-v1':
                analyze_func = analyze_sentiment_llm
            else:
                print(f"  ⚠️  Unknown generator type: {generator_type}")
                continue

            generator_signals = []

            # Analyze each article
            for i, article in enumerate(articles, 1):
                currency = article['currency']
                title = article['title']
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

                # Calculate base_signal based on direction and magnitude
                # Positive if bullish, negative if bearish
                # Scaled by magnitude: small=0.4, medium=0.7, large=1.0
                magnitude_multipliers = {
                    'small': 0.4,
                    'medium': 0.7,
                    'large': 1.0
                }

                if signal_direction == 'neutral' or not predicted_magnitude:
                    base_signal = 0.0
                elif signal_direction == 'bullish':
                    base_signal = magnitude_multipliers.get(predicted_magnitude, 0.7)
                elif signal_direction == 'bearish':
                    base_signal = -magnitude_multipliers.get(predicted_magnitude, 0.7)
                else:
                    base_signal = 0.0

                # Calculate final signal value (confidence × base_signal)
                signal_value = round(confidence * base_signal, 4)

                # Get horizon data for this article and currency
                horizon_key = (article.get('article_id', ''), currency)
                horizon = horizon_lookup.get(horizon_key)
                estimator_id = horizon['estimator_id'] if horizon else 'unknown'
                valid_to_date = horizon['valid_to_date'] if horizon else ''

                # Build CSV row
                signal = {
                    'date': date_str,
                    'article_id': article.get('article_id', ''),
                    'currency': currency,
                    'pair_context': pair_context if pair_context else None,
                    'estimator_id': estimator_id,
                    'valid_to_date': valid_to_date,
                    'generator_id': gen_id,
                    'predicted_direction': signal_direction,
                    'predicted_magnitude': predicted_magnitude if predicted_magnitude else None,
                    'base_signal': round(base_signal, 4),
                    'confidence': confidence,
                    'signal': signal_value,
                    'reasoning': reasoning
                }

                generator_signals.append(signal)
                all_signals.append(signal)

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

            print(f"\n✓ Generator {gen_id}: {len(generator_signals)} signals")
            print(f"  Bullish: {bullish}, Bearish: {bearish}, Neutral: {neutral}")
            print(f"  Avg confidence: {avg_conf:.2f}")

        logger.add_count('total_signals', len(all_signals))
        logger.add_count('generators_executed', len(summary_by_generator))

        # Write to CSV
        print(f"\n2. Saving to CSV...")
        if all_signals:
            csv_path = write_csv(all_signals, 'process_5_signals', date=date_str)
            print(f"   ✓ Saved {len(all_signals)} signals to {csv_path}")
            logger.add_info('output_file', str(csv_path))
        else:
            print(f"   ⚠ No signals to save")
            logger.warning("No signals generated")

        # Summary
        print(f"\n{'='*60}")
        print(f"✓ Generated {len(all_signals)} total signals from {len(summary_by_generator)} generators")
        print(f"{'='*60}")

        if summary_by_generator:
            print("\nGenerator Summary:")
            print(f"{'Generator':<40} {'Total':<8} {'Bull':<6} {'Bear':<6} {'Neut':<6} {'Conf':<6}")
            print("-" * 72)
            for gen_id, stats in summary_by_generator.items():
                print(f"{gen_id:<40} {stats['total']:<8} {stats['bullish']:<6} {stats['bearish']:<6} {stats['neutral']:<6} {stats['avg_confidence']:<6.2f}")

        logger.success()

    except Exception as e:
        logger.error(f"Failed to generate signals: {str(e)}")
        logger.fail()
        raise
    finally:
        logger.finish()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate sentiment signals from news')
    parser.add_argument('--date', type=str, help='Date to process (YYYY-MM-DD), defaults to today')
    args = parser.parse_args()

    main(date_str=args.date)
