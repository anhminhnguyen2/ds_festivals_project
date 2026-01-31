import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id="YOUR_ID", client_secret="YOUR_SECRET"))

artist_uri = 'spotify:artist:4y7D92uRM7070S4Y70O9Xv' # Example: Anyma
artist = sp.artist(artist_uri)
print(f"Current Popularity: {artist['popularity']}")