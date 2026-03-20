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


def load_currency_events():
    """Load currency events taxonomy from Step 4.1"""
    events_path = '/workspace/group/fx-portfolio/data/events/currency_events.json'
    with open(events_path, 'r') as f:
        data = json.load(f)
    return data['events']


def analyze_sentiment_event_keywords(combined_text, currency, params, currency_events):
    """
    Event-based keyword sentiment analysis

    Matches article text against currency events taxonomy to determine
    which events are indicated and their strength.

    Args:
        combined_text: Article title + snippet
        currency: 3-letter currency code
        params: Generator parameters
        currency_events: List of event dictionaries from Step 4.1

    Returns:
        list: List of (event_id, signal, confidence, reasoning) tuples for matching events
    """
    import re

    text_lower = combined_text.lower()
    matched_events = []

    # Track bullish vs bearish matches for fallback
    bullish_matches = 0
    bearish_matches = 0

    for event in currency_events:
        event_id = event['event_id']
        event_signal = event['signal']
        keywords = event.get('keywords', [])
        required_keywords = event.get('required_keywords', [])

        # Check if required keywords are present (if any are specified)
        if required_keywords:
            has_required = any(req_kw.lower() in text_lower for req_kw in required_keywords)
            if not has_required:
                continue  # Skip this event if required keywords not found

        # Count matching keywords from the event
        keyword_matches = sum(1 for kw in keywords if kw.lower() in text_lower)

        if keyword_matches == 0:
            continue  # No keywords matched

        # Track generic bullish/bearish matches for fallback
        if event_id == 'bullish_signal':
            bullish_matches = keyword_matches
        elif event_id == 'bearish_signal':
            bearish_matches = keyword_matches

        # Calculate event strength based on keyword matches
        # Use more generous threshold: 1 match = 10% strength minimum
        # Scale up to 100% strength with more matches
        max_keywords = len(keywords)
        # Use 10 keywords as threshold (about 30% of typical event keyword list)
        strength = min(1.0, keyword_matches / max(1, 10))  # 1 match = 0.1, 10 matches = 1.0

        # Calculate confidence based on match quality
        # More matches = higher confidence
        confidence = min(0.9, 0.3 + (keyword_matches * 0.08))  # 0.3 base + 0.08 per match, max 0.9

        # Calculate final signal = strength × event_signal
        final_signal = round(strength * event_signal, 4)

        reasoning = f"{event['event_name']}: {keyword_matches} keyword matches"

        matched_events.append((event_id, final_signal, confidence, reasoning))

    # Return matched events (empty list if no events detected)
    # In event-based framework, no events = no signals (not neutral)
    return matched_events


def analyze_sentiment_llm(combined_text, currency, params, currency_events):
    """
    Event-based LLM sentiment analysis using Claude Haiku

    Evaluates article against all currency events and returns strength scores
    for each relevant event.

    Args:
        combined_text: Article title + snippet
        currency: 3-letter currency code
        params: Generator parameters (model, temperature, etc.)
        currency_events: List of event dictionaries from Step 4.1

    Returns:
        list: List of (event_id, signal, confidence, reasoning) tuples for matching events
    """
    api_key = get_anthropic_key()
    if not api_key:
        print("  ⚠️  Anthropic API key not found, returning empty list")
        return []

    # Build event list for prompt
    event_descriptions = []
    for event in currency_events:
        event_id = event['event_id']
        event_name = event['event_name']
        event_signal = event['signal']
        description = event.get('description', '')

        # Determine polarity for clarity
        polarity = "BULLISH" if event_signal > 0 else "BEARISH" if event_signal < 0 else "NEUTRAL"

        event_descriptions.append(
            f"- **{event_id}** ({polarity}, signal={event_signal}): {event_name}\n  {description}"
        )

    events_text = "\n".join(event_descriptions)

    # Build prompt
    prompt = f"""You are an expert FX market analyst. Analyze this news article for {currency} and identify which currency events (if any) are indicated.

**Article Text**:
{combined_text}

**Currency Events to Consider**:
{events_text}

**Your Task**:
For each event that this article clearly indicates or discusses, assign a strength score (0.0-1.0):
- 1.0 = Very strong indication of this event
- 0.7 = Clear indication
- 0.5 = Moderate indication
- 0.3 = Weak indication
- 0.0 = No indication (DON'T include in response)

**CRITICAL RULES**:
1. ONLY include events that are actually discussed or indicated in the article
2. DO NOT make up events or assign strengths without clear evidence
3. If the article doesn't clearly indicate any specific event, return an empty array
4. Use generic bullish_signal/bearish_signal ONLY if no specific event applies but there's clear directional sentiment
5. For FX pairs: "{currency}/XXX rises" = bullish for {currency}, "XXX/{currency} rises" = bearish for {currency}

**Output Format (JSON)**:
{{
  "events": [
    {{
      "event_id": "event_id_from_list",
      "strength": 0.0-1.0,
      "reasoning": "brief explanation why this event applies"
    }}
  ]
}}

Return ONLY the JSON array. If no events match, return {{"events": []}}."""

    # Call Anthropic API
    try:
        url = "https://api.anthropic.com/v1/messages"
        request_body = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 500,  # Increased for multiple events
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

            # Extract JSON from response (handle markdown code blocks and nested structures)
            import re
            # Remove markdown code blocks if present
            response_text = re.sub(r'```json\s*', '', response_text)
            response_text = re.sub(r'```\s*$', '', response_text)
            response_text = response_text.strip()

            # Try to find JSON object (including nested arrays)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not json_match:
                print(f"  ⚠️  Failed to find JSON in LLM response")
                return []

            try:
                analysis = json.loads(json_match.group(0))
            except json.JSONDecodeError as e:
                # Silently skip parse errors - LLM may have returned malformed JSON
                return []
            detected_events = analysis.get('events', [])

            if not detected_events:
                return []  # No events detected

            # Convert to output format
            matched_events = []
            event_lookup = {e['event_id']: e for e in currency_events}

            for detected in detected_events:
                event_id = detected.get('event_id')
                strength = float(detected.get('strength', 0))
                reasoning = detected.get('reasoning', 'LLM analysis')

                # Validate event_id exists
                if event_id not in event_lookup:
                    continue

                event = event_lookup[event_id]
                event_signal = event['signal']

                # Calculate final signal = strength × event_signal
                final_signal = round(strength * event_signal, 4)

                # Use strength as confidence
                confidence = round(min(0.9, strength), 2)

                matched_events.append((event_id, final_signal, confidence, reasoning))

            return matched_events

    except Exception as e:
        print(f"  ⚠️  LLM API error: {str(e)[:100]}")
        return []


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

        if not articles or not horizons:
            print(f"   ⚠ No articles/horizons to analyze")
            print(f"\n3. Saving empty CSV...")
            # Create empty CSV file for downstream processes
            csv_path = write_csv([], 'process_5_signals', date=date_str)
            print(f"   ✓ Saved empty CSV (0 signals) to {csv_path}")
            logger.warning("No articles/horizons found - empty CSV created")
            logger.success()
            return

        # Load currency events for event-based keyword matching
        currency_events = load_currency_events()
        print(f"\n✓ Loaded {len(currency_events)} currency events from Step 4.1")

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

            # Determine if this is event-based keyword or traditional analysis
            is_event_based_keyword = (generator_type == 'keyword-sentiment-v1.1')
            is_llm = (generator_type == 'llm-sentiment-v1')

            if not is_event_based_keyword and not is_llm:
                print(f"  ⚠️  Unknown generator type: {generator_type}")
                continue

            generator_signals = []

            # Analyze each article
            for i, article in enumerate(articles, 1):
                currency = article['currency']
                title = article['title']
                article_text = f"{title} {article.get('snippet', '')}"

                # Get horizon data for this article and currency
                horizon_key = (article.get('article_id', ''), currency)
                horizon = horizon_lookup.get(horizon_key)
                estimator_id = horizon['estimator_id'] if horizon else 'unknown'
                valid_to_date = horizon['valid_to_date'] if horizon else ''

                if is_event_based_keyword:
                    # Event-based keyword matching
                    matched_events = analyze_sentiment_event_keywords(
                        article_text, currency, generator_params, currency_events
                    )

                    # Create one signal per matched event
                    for event_id, signal_value, confidence, reasoning in matched_events:
                        # Skip zero/neutral signals - event framework only outputs activated events
                        if signal_value == 0:
                            continue

                        # Determine direction and magnitude from signal value
                        if signal_value > 0:
                            direction = 'bullish'
                            magnitude = 'large' if signal_value >= 0.7 else 'medium' if signal_value >= 0.4 else 'small'
                        else:  # signal_value < 0
                            direction = 'bearish'
                            magnitude = 'large' if abs(signal_value) >= 0.7 else 'medium' if abs(signal_value) >= 0.4 else 'small'

                        signal = {
                            'date': date_str,
                            'article_id': article.get('article_id', ''),
                            'currency': currency,
                            'pair_context': None,  # Event-based doesn't use pair context
                            'estimator_id': estimator_id,
                            'valid_to_date': valid_to_date,
                            'generator_id': gen_id,
                            'event_id': event_id,  # Actual event ID from taxonomy
                            'predicted_direction': direction,
                            'predicted_magnitude': magnitude,
                            'base_signal': round(signal_value, 4),  # Signal comes directly from event match
                            'confidence': confidence,
                            'signal': signal_value,
                            'reasoning': reasoning
                        }

                        generator_signals.append(signal)
                        all_signals.append(signal)

                elif is_llm:
                    # Event-based LLM sentiment analysis
                    matched_events = analyze_sentiment_llm(
                        article_text, currency, generator_params, currency_events
                    )

                    # If no events detected, skip this article (LLM found nothing relevant)
                    if not matched_events:
                        continue

                    # Check for FX pair mentions (for reasoning context)
                    base_curr, quote_curr = detect_fx_pair(title)
                    pair_context = None

                    if base_curr and quote_curr:
                        pair_context = f"{base_curr}/{quote_curr}"

                    # Create one signal per matched event
                    for event_id, signal_value, confidence, reasoning in matched_events:
                        # Skip zero/neutral signals - event framework only outputs activated events
                        if signal_value == 0:
                            continue

                        # Determine direction and magnitude from signal value
                        if signal_value > 0:
                            direction = 'bullish'
                            magnitude = 'large' if abs(signal_value) >= 0.7 else 'medium' if abs(signal_value) >= 0.4 else 'small'
                        else:  # signal_value < 0
                            direction = 'bearish'
                            magnitude = 'large' if abs(signal_value) >= 0.7 else 'medium' if abs(signal_value) >= 0.4 else 'small'

                        # Add pair context to reasoning if applicable
                        if pair_context:
                            reasoning = f"{pair_context}: {reasoning}"

                        signal = {
                            'date': date_str,
                            'article_id': article.get('article_id', ''),
                            'currency': currency,
                            'pair_context': pair_context,
                            'estimator_id': estimator_id,
                            'valid_to_date': valid_to_date,
                            'generator_id': gen_id,
                            'event_id': event_id,  # Actual event ID from LLM analysis
                            'predicted_direction': direction,
                            'predicted_magnitude': magnitude,
                            'base_signal': round(signal_value, 4),
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
