#!/usr/bin/env python3
"""
Cross-Date News Deduplication Utility

Removes duplicate articles across different dates.
Strategy: Keep first occurrence, remove from later dates.

Example:
- March 7: Article X (kept)
- March 8: Article X (removed - already in March 7)
- March 9: Article X (removed - already in March 7)
"""

import glob
import sys
from pathlib import Path

sys.path.append('/workspace/group/fx-portfolio/scripts')
from utilities.csv_helper import read_csv, write_csv

BASE_DIR = Path('/workspace/group/fx-portfolio')
NEWS_DIR = BASE_DIR / 'data' / 'news'


def main():
    """Deduplicate news articles across all dates"""
    print("=" * 70)
    print("Cross-Date News Deduplication Utility")
    print("=" * 70)
    print()

    # Find all news CSV files (sorted by date)
    news_files = sorted(glob.glob(str(NEWS_DIR / '*.csv')))

    if not news_files:
        print("No news files found in data/news/")
        return

    print(f"Found {len(news_files)} news files to process")
    print()

    # Track URLs we've seen (globally across all dates)
    global_seen_urls = set()

    total_original = 0
    total_kept = 0
    total_removed = 0
    files_modified = 0

    # Process each file in chronological order
    for filepath in news_files:
        # Extract date from filename
        filename = Path(filepath).stem
        date_str = filename

        try:
            # Read articles for this date
            articles = read_csv('3', date=date_str, validate=False)
            original_count = len(articles)
            total_original += original_count

            # Filter: keep only articles we haven't seen before
            unique_articles = []
            local_duplicates = 0

            for article in articles:
                url = article['url']
                if url not in global_seen_urls:
                    unique_articles.append(article)
                    global_seen_urls.add(url)
                else:
                    local_duplicates += 1

            kept_count = len(unique_articles)
            total_kept += kept_count
            total_removed += local_duplicates

            # Rewrite file if we removed any duplicates
            if local_duplicates > 0:
                write_csv(unique_articles, '3', date=date_str)
                files_modified += 1
                print(f"✓ {date_str}: {original_count} → {kept_count} articles (-{local_duplicates} duplicates)")
            else:
                print(f"  {date_str}: {original_count} articles (no duplicates)")

        except FileNotFoundError:
            print(f"  {date_str}: File not found (skipped)")
        except Exception as e:
            print(f"  ✗ {date_str}: Error - {e}")

    # Summary
    print()
    print("=" * 70)
    print("Cross-Date Deduplication Summary")
    print("=" * 70)
    print(f"Files processed: {len(news_files)}")
    print(f"Files modified: {files_modified}")
    print(f"Total articles before: {total_original}")
    print(f"Total articles after: {total_kept}")
    print(f"Total duplicates removed: {total_removed}")

    if total_removed > 0:
        reduction_pct = (total_removed / total_original) * 100
        print(f"Reduction: {reduction_pct:.1f}%")

    print("=" * 70)
    print()

    if total_removed > 0:
        print(f"✓ Deduplication complete! Removed {total_removed} duplicate articles across dates.")
        print(f"  First occurrence of each article was kept, later occurrences removed.")
    else:
        print("✓ No cross-date duplicates found!")


if __name__ == '__main__':
    main()
