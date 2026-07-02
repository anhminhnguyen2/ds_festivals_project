"""Scrape Songstats popularity metrics for every artist in the candidate pool.

Meant to be run MONTHLY. Each sweep gets its own date-stamped snapshot in
data/metrics_snapshots/ (artist_stats_YYYY-MM-DD.csv, dated when the sweep
started, so the file name tells you when the data was collected).

Resume rules:
- Re-running the script continues this month's unfinished sweep, skipping
  artists already collected but RETRYING artists that errored last time.
- Once this month's sweep is complete, the script exits and tells you so
  (pass --new to force a fresh sweep anyway).
- In a new month, a new snapshot file starts automatically.

Usage:
    python artist_metrics.py              # scrape all remaining artists
    python artist_metrics.py --batch 50   # scrape at most 50 artists this run
    python artist_metrics.py --new        # force-start a fresh sweep today
"""
import pandas as pd
import argparse
import glob
import os
import random
import re
import time
from datetime import datetime

# --- CONFIGURATION ---
script_dir = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT_DIR = os.path.join(script_dir, 'data', 'metrics_snapshots')

# Every artist we know about: the master dataset plus the deduplicated lineup
# list (the latter picks up newly scraped artists before they reach the master).
ARTIST_SOURCES = [
    os.path.join(script_dir, 'data', 'main', 'COMPLETE_edc_artist_and_stats.csv'),
    os.path.join(script_dir, 'data', 'main', 'edc_artists_no_duplicates.csv'),
]


def norm_name(s):
    """Same normalization as the rest of the pipeline, so names join cleanly."""
    s = str(s).lower().strip().replace('&', 'and')
    return re.sub(r'\s+', ' ', s)


def load_artists():
    names, seen = [], set()
    for path in ARTIST_SOURCES:
        try:
            for raw in pd.read_csv(path)['artist'].dropna().astype(str):
                n = norm_name(raw)
                if n and n not in seen:
                    seen.add(n)
                    names.append(n)
        except Exception as e:
            print(f"Warning: could not read {path}: {e}")
    return names


def error_mask(df):
    if 'Error' not in df.columns:
        return pd.Series(False, index=df.index)
    return df['Error'].notna() & (df['Error'].astype(str).str.strip() != '')


def pick_output_file(force_new):
    """Return the snapshot file for this run (this month's sweep, resumed if
    it already exists), or a fresh date-stamped file in a new month."""
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    snapshots = sorted(glob.glob(os.path.join(SNAPSHOT_DIR, 'artist_stats_????-??-??.csv')))
    today = datetime.now()
    new_file = os.path.join(SNAPSHOT_DIR, f"artist_stats_{today:%Y-%m-%d}.csv")

    if force_new or not snapshots:
        return new_file

    latest = snapshots[-1]
    latest_date = datetime.strptime(os.path.basename(latest), 'artist_stats_%Y-%m-%d.csv')
    if (latest_date.year, latest_date.month) != (today.year, today.month):
        return new_file  # new month -> new sweep

    return latest  # same month -> resume this month's sweep


def scrape_songstats(batch_size=0, force_new=False):
    from playwright.sync_api import sync_playwright

    artists = load_artists()
    if not artists:
        print("No artists found in the source CSVs - nothing to do.")
        return

    output_file = pick_output_file(force_new)

    # --- RESUME LOGIC ---
    # Artists already in the file count as processed ONLY if they have no
    # error; errored rows are dropped so they get retried this run.
    # With --new the existing file is ignored and overwritten from scratch.
    existing_df = pd.DataFrame()
    processed_artists = set()
    if os.path.exists(output_file) and not force_new:
        try:
            existing_df = pd.read_csv(output_file)
            errored = error_mask(existing_df)
            n_err = int(errored.sum())
            existing_df = existing_df[~errored].reset_index(drop=True)
            processed_artists = set(existing_df['Artist'].map(norm_name))
            print(f"Resuming {os.path.basename(output_file)}: "
                  f"{len(processed_artists)} artists done, {n_err} errored (will retry).")
        except Exception as e:
            print(f"Error reading existing file: {e}")

    remaining_artists = [a for a in artists if a not in processed_artists]
    if not remaining_artists:
        print(f"This month's sweep ({os.path.basename(output_file)}) is complete: "
              f"{len(processed_artists)} artists. Use --new to force a fresh sweep.")
        return

    if batch_size and len(remaining_artists) > batch_size:
        print(f"Batching: next {batch_size} of {len(remaining_artists)} remaining artists.")
        artists_to_process = remaining_artists[:batch_size]
    else:
        print(f"Processing all {len(remaining_artists)} remaining artists.")
        artists_to_process = remaining_artists

    data_results = []

    def save_progress():
        current_df = pd.DataFrame(data_results)
        combined_df = pd.concat([existing_df, current_df], ignore_index=True) \
            if not existing_df.empty else current_df
        combined_df.to_csv(output_file, index=False)
        return len(combined_df)

    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print("Opening Songstats...")
        page.goto("https://songstats.com/welcome")

        # Initial safe pause
        time.sleep(random.randint(3, 5))

        for i, artist in enumerate(artists_to_process):
            print(f"[{i+1}/{len(artists_to_process)}] Processing: {artist}")
            row_data = {"Artist": artist}

            try:
                # 1. ALWAYS go to welcome page to reset state and search bar
                page.goto("https://songstats.com/welcome")
                page.wait_for_load_state("networkidle")
                time.sleep(random.uniform(2, 4))

                # 2. Search
                # Locate the search bar using the specific ID found in devtools
                # Fallback to other selectors if ID not found
                search_input = page.locator('#entitySearchBarInput')
                if search_input.count() == 0:
                     search_input = page.locator('input[placeholder*="Search"], input[aria-label*="Search"], input[type="text"]').first

                search_input.click()
                search_input.fill(artist)
                time.sleep(random.randint(1, 3)) # Wait for dropdown results to populate

                # 2. Select the first result
                # Instruction: Press Enter, choose Artists tab, choose top option.
                page.keyboard.press("Enter")
                time.sleep(random.randint(1, 3))

                # Click "Artists" filter tab to ensure we get artists
                try:
                    # We look for the "Artists" text and click it.
                    page.get_by_text("Artists", exact=True).first.click()
                    time.sleep(random.randint(2, 6))
                except Exception:
                    pass # Continue if tab not found

                # If we are not on an artist page (URL doesn't contain /artist/), try clicking the first result
                if "/artist/" not in page.url:
                    # Choose the top option in the artist tab
                    # We try to click the element containing the artist name text.
                    try:
                        # This finds the first visible element with the artist name text
                        page.get_by_text(artist).first.click()
                    except:
                        print(f"   -> Could not find text '{artist}', trying generic first result")
                        # Fallback: click the first result container (heuristic)
                         # We look for a link to an artist page or just the first image
                        page.locator('a[href*="/artist/"]').first.click()

                    time.sleep(random.randint(2, 6))

                # 3. Extract Info
                # Check if we are on a valid page
                if "/artist/" in page.url:
                    # We are on the artist page
                    # Metrics to extract
                    metrics = [
                        "Followers", "Streams", "Playlists", "Playlist Reach",
                        "Charts", "Shazams", "Videos", "Views", "DJ Supports"
                    ]

                    # Logic: Find the row containing the metric label, then get the value.
                    # Based on screenshot: Labels are in <div ...>Label</div>
                    # The value is usually in a sibling div inside the same parent row container.
                    # Or the parent contains "Label\nValue".

                    for metric in metrics:
                        try:
                            # 1. Find the element containing the exact Metric Name
                            # We use xpath to find the span containing the text, then find the ancestor row.
                            # The row in the screenshot has "justify-content: space-between".
                            # logic: //span[text()='Metric']/ancestor::div[contains(@style, 'justify-content: space-between')][1]

                            # Note: Songstats text might be in span or div.
                            # We'll construct an xpath that looks for the text, then goes up to the row.
                            xpath_selector = f"//*[text()='{metric}']/ancestor::div[contains(@style, 'justify-content: space-between')]"

                            row_locator = page.locator(xpath_selector).first

                            if row_locator.count() > 0:
                                # Get all text from that row.
                                # Expected format: "Followers\n[Icons if any]\n641K"
                                row_text = row_locator.inner_text()

                                # Split by newline. The value is usually the last item (right side).
                                parts = [p.strip() for p in row_text.split('\n') if p.strip()]

                                # We want the value at the end.
                                # Example parts: ['Followers', '641K']
                                value = parts[-1] if parts else "N/A"

                                # Safety: if the value we extracted is just the metric name again, then we failed to get the value
                                if value == metric:
                                    value = "N/A"

                                row_data[metric] = value
                            else:
                                # Fallback: try traversing up 3-4 levels blindly if specific style match fails
                                label_el = page.get_by_text(metric, exact=True).first
                                if label_el.is_visible():
                                    # span -> div -> div -> div (row)
                                    parent = label_el.locator("xpath=./../..").locator("xpath=./..")
                                    text = parent.inner_text()
                                    parts = [p.strip() for p in text.split('\n') if p.strip()]
                                    row_data[metric] = parts[-1] if parts else "N/A"
                                else:
                                    row_data[metric] = "N/A"

                        except Exception as e:
                            # print(f"Debug: Error extracting {metric}: {e}")
                            row_data[metric] = "N/A"

                    print(f"   -> Data: {row_data}")

                else:
                    print("   -> Could not navigate to artist page.")
                    row_data["Error"] = "Navigation Failed"

                data_results.append(row_data)

                # Brief pause between artists
                time.sleep(random.uniform(3, 6))

            except Exception as e:
                print(f"   -> Error on {artist}: {e}")
                row_data["Error"] = str(e)
                data_results.append(row_data)

            # Save periodically
            if (i + 1) % 10 == 0:
                n = save_progress()
                print(f"   -> Progress saved ({n} records).")

        browser.close()

    # Final Save
    n = save_progress()
    print(f"Done. Saved {n} records to {output_file}")

    n_left = len(remaining_artists) - len(artists_to_process)
    if n_left > 0:
        print(f"[INFO] {n_left} artists remaining. Run the script again to continue.")
    else:
        print("Sweep complete for this month.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monthly Songstats metrics sweep.")
    parser.add_argument('--batch', type=int, default=0,
                        help="max artists to scrape this run (default: all remaining)")
    parser.add_argument('--new', action='store_true',
                        help="force-start a fresh sweep dated today")
    args = parser.parse_args()
    scrape_songstats(batch_size=args.batch, force_new=args.new)
