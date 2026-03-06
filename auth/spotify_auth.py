import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os

load_dotenv() # load environment variables from .env file

SCOPES = " ".join([
    "user-read-playback-state",
    "user-modify-playback-state",
    "user-read-currently-playing",
    "playlist-read-private",
    "user-library-read",
])

def get_spotify_client():
    """
    Creates and returns an authenticated Spotipy client.
    On first run, this wil open a browser for Spotify login.
    On subsequent runs, it uses the cached token automatically.
    """

    auth_manager = SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
        scope=SCOPES,
        cache_path=".cache", # this will store the token for Spotipy to use
    )

    # create the spotipy client with the auth manager
    return spotipy.Spotify(auth_manager=auth_manager)

if __name__ == "__main__":
    sp = get_spotify_client()

    user = sp.current_user()
    print(f"Logged in as: {user['display_name']}")