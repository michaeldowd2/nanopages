#!/usr/bin/env python3
"""
Article ID Generator

Generates deterministic short IDs from article URLs for easier reference
and tracking across the pipeline.
"""

import hashlib


def generate_article_id(url: str) -> str:
    """
    Generate a short, deterministic article ID from URL.

    Args:
        url: Article URL

    Returns:
        12-character hexadecimal hash (first 12 chars of SHA256)

    Examples:
        >>> generate_article_id('https://www.fxstreet.com/news/article-123')
        'a3f2c8d91e5b'
    """
    if not url:
        return ''

    # Use SHA256 and take first 12 characters (48 bits)
    # This gives ~281 trillion possible IDs - more than enough for our use case
    return hashlib.sha256(url.encode('utf-8')).hexdigest()[:12]


if __name__ == '__main__':
    # Test examples
    test_urls = [
        'https://www.fxstreet.com/news/usd-jpy-forecast-pair-trades-sideways-around-14950-ahead-of-us-pce-data-20260224',
        'https://www.forexlive.com/news/fed-officials-signal-patience-20260225',
        'https://www.reuters.com/markets/currencies/dollar-holds-gains-2026-03-11'
    ]

    print("Article ID Generation Test:")
    print("=" * 70)
    for url in test_urls:
        article_id = generate_article_id(url)
        print(f"{article_id} <- {url}")
