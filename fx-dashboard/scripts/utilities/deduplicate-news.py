#!/usr/bin/env python3
"""
News Deduplication Utility

Removes duplicate articles from existing news CSV files.
For each date, checks all articles and removes duplicates based on URL.

Strategy:
- For each date's CSV file
- Load all articles
- Keep only unique URLs (first occurrence wins)
- Rewrite the CSV with deduplicated data
"""

import glob
import csv
import sys
from pathlib import Path
from collections import OrderedDict

sys.path.append('/workspace/group/fx-portfolio/scripts')
from utilities.csv_helper import read_csv, write_csv

BASE_DIR = Path('/workspace/group/fx-portfolio')
NEWS_DIR = BASE_DIR / 'data' / 'news'


def deduplicate_file(date_str):
    """
    Deduplicate a single news CSV file by URL.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        Tuple of (original_count, deduplicated_count, duplicates_removed)
    """
    try:
        # Read all articles for this date
        articles = read_csv('3', date=date_str, validate=False)

        if not articles:
            return 0, 0, 0

        original_count = len(articles)

        # Deduplicate by URL (keep first occurrence)
        seen_urls = set()
        unique_articles = []

        for article in articles:
            url = article['url']
            if url not in seen_urls:
                unique_articles.append(article)
                seen_urls.add(url)

        deduplicated_count = len(unique_articles)
        duplicates_removed = original_count - deduplicated_count

        # Only rewrite if we removed duplicates
        if duplicates_removed > 0:
            write_csv(unique_articles, '3', date=date_str)

        return original_count, deduplicated_count, duplicates_removed

    except FileNotFoundError:
        return 0, 0, 0
    except Exception as e:
        print(f"   ✗ Error processing {date_str}: {e}")
        return 0, 0, 0


def main():
    """Deduplicate all existing news CSV files"""
    print("=" * 70)
    print("News Deduplication Utility")
    print("=" * 70)
    print()

    # Find all news CSV files
    news_files = sorted(glob.glob(str(NEWS_DIR / '*.csv')))

    if not news_files:
        print("No news files found in data/news/")
        return

    print(f"Found {len(news_files)} news files to process")
    print()

    total_original = 0
    total_deduplicated = 0
    total_duplicates_removed = 0
    files_with_duplicates = 0

    # Process each file
    for filepath in news_files:
        # Extract date from filename
        filename = Path(filepath).stem
        date_str = filename

        original, deduplicated, removed = deduplicate_file(date_str)

        if original > 0:
            total_original += original
            total_deduplicated += deduplicated
            total_duplicates_removed += removed

            if removed > 0:
                files_with_duplicates += 1
                print(f"✓ {date_str}: {original} → {deduplicated} articles (-{removed} duplicates)")
            else:
                print(f"  {date_str}: {original} articles (no duplicates)")

    # Summary
    print()
    print("=" * 70)
    print("Deduplication Summary")
    print("=" * 70)
    print(f"Files processed: {len(news_files)}")
    print(f"Files with duplicates: {files_with_duplicates}")
    print(f"Total articles before: {total_original}")
    print(f"Total articles after: {total_deduplicated}")
    print(f"Total duplicates removed: {total_duplicates_removed}")

    if total_duplicates_removed > 0:
        reduction_pct = (total_duplicates_removed / total_original) * 100
        print(f"Reduction: {reduction_pct:.1f}%")

    print("=" * 70)
    print()

    if total_duplicates_removed > 0:
        print(f"✓ Deduplication complete! Removed {total_duplicates_removed} duplicate articles.")
    else:
        print("✓ No duplicates found - all files are clean!")


if __name__ == '__main__':
    main()
