from playwright.sync_api import sync_playwright
import time
import pandas as pd
import os

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

output_file = "artist_popularity.csv"
# Construct path relative to the script location
input_csv = os.path.join(script_dir, 'data', 'main', 'edc_all_artists.csv')

artists = pd.read_csv(input_csv)['artist'].tolist()
data_results = []

def scrape_musicstax():
    with sync_playwright() as p:
        # Launch browser (headless=False lets you see what's happening)
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        for artist in artists:
            try:
                # 1. Go to the home page
                page.goto("https://musicstax.com/")
                
                # 2. Type artist name into the search bar 
                # The screenshot shows a placeholder "Search by track or artist"
                search_input = page.get_by_placeholder("Search by track or artist")
                search_input.fill(artist)
                search_input.press("Enter")
                
                # 3. Wait for search results and click the first artist
                # Most search flows require clicking the result to get to the profile
                # We assume the first result is the most relevant artist
                page.wait_for_selector('a[href^="/artist/"]', timeout=5000)
                page.locator('a[href^="/artist/"]').first.click()
                
                # 4. Extract the popularity score
                # We look for the container having "Spotify Popularity" and then find the big number
                page.wait_for_selector("text=Spotify Popularity", timeout=10000)
                
                # Locate the container for popularity based on text "Spotify Popularity"
                # Then look for the span with the large text class seen in the screenshot
                popularity_container = page.locator("div").filter(has_text="Spotify Popularity").last
                popularity = popularity_container.locator("span.text-4xl").inner_text()
                
                print(f"Artist: {artist} | Popularity: {popularity}")
                data_results.append({"Artist": artist, "Popularity": popularity})
                
                # 5. Ethical delay
                time.sleep(2) 
                
            except Exception as e:
                print(f"Error finding {artist}: {e}")
                data_results.append({"Artist": artist, "Popularity": "Not Found"})

        browser.close()

    # Save to CSV for your EDA phase
    df = pd.DataFrame(data_results)
    df.to_csv(output_file, index=False)

scrape_musicstax()