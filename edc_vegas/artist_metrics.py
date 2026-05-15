from playwright.sync_api import sync_playwright
import pandas as pd
import time
import random
import os
from datetime import datetime

# --- CONFIGURATION ---
# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

mmyyyy = datetime.now().strftime('%m%Y')
output_file = os.path.join(script_dir, 'data', 'main', f"edc_artist_stats_{mmyyyy}.csv")
input_csv = os.path.join(script_dir, 'data', 'main', 'edc_artists_no_duplicates.csv')

# Load artists
try:
    artists = pd.read_csv(input_csv)['artist'].tolist()
except Exception as e:
    print(f"Error loading CSV: {e}")
    # Fallback for testing if file missing
    artists = ["Knock2", "Subtronics"] 

data_results = []

def scrape_songstats():
    # --- RESUME & BATCH LOGIC ---
    processed_artists = set()
    existing_df = pd.DataFrame()
    
    if os.path.exists(output_file):
        try:
            existing_df = pd.read_csv(output_file)
            if 'Artist' in existing_df.columns:
                processed_artists = set(existing_df['Artist'].tolist())
            print(f"Resuming: Found {len(processed_artists)} already processed artists.")
        except Exception as e:
            print(f"Error reading existing file: {e}")

    # Filter artists
    remaining_artists = [a for a in artists if a not in processed_artists]
    
    # Batch limit
    BATCH_SIZE = 20
    if len(remaining_artists) > BATCH_SIZE:
        print(f"Batching: Selecting next {BATCH_SIZE} artists from {len(remaining_artists)} remaining.")
        artists_to_process = remaining_artists[:BATCH_SIZE]
    else:
        print(f"Processing remaining {len(remaining_artists)} artists.")
        artists_to_process = remaining_artists

    if not artists_to_process:
        print("All artists have been processed!")
        return

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
                current_df = pd.DataFrame(data_results)
                # Combine with existing
                if not existing_df.empty:
                    combined_df = pd.concat([existing_df, current_df], ignore_index=True)
                else:
                    combined_df = current_df
                
                combined_df.to_csv(output_file, index=False)
                print(f"   -> Progress saved ({len(combined_df)} records).")

        browser.close()
    
    # Final Save
    current_df = pd.DataFrame(data_results)
    if not existing_df.empty:
        combined_df = pd.concat([existing_df, current_df], ignore_index=True)
    else:
        combined_df = current_df
    combined_df.to_csv(output_file, index=False)
    print(f"Done. Saved to {output_file}")
    
    if len(remaining_artists) > BATCH_SIZE:
         print("[INFO] Batch complete. Run the script again to continue.")
    else:
         print("All tasks complete.")

if __name__ == "__main__":
    scrape_songstats()