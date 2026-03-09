from auth.spotify_auth import get_spotify_client

# get authenticated client
# every function below will use this client instance
sp = get_spotify_client()


# --- playback controls ---

def play():
    sp.start_playback()

def pause():
    sp.pause_playback()

def next_track():
    sp.next_track()

def previous_track():
    sp.previous_track()

def set_volume(level: int):
    sp.volume(level) # volume must be between 0 - 100

def toggle_shuffle():
    sp.shuffle(state) # true = shuffle on | false = shuffle off

def toggle_repeat():
    sp.repeat(state) # options: 'track' | 'context' (album/playlist) | 'off'

def play_uri(track_uri: str):
    sp.start_playback(uris=[track_uri]) # track_uri looks like "spotify:track:4iV5W9uYEdYUVa79Axb7Rh"

def play_context_uri(context_uri: str):
    """Play an album or playlist by its context URI."""
    sp.start_playback(context_uri=context_uri) # e.g. "spotify:album:..." or "spotify:playlist:..."


# --- now playing ---

def get_current_track():
    """
    Returns the full playback state from Spotify.
    The rest of the app will pull what's needed from this source.
    """
    return sp.current_playback()


# --- search ---
def search(query: str, search_type: str = "track", limit: int = 10):
    """
    Searches the Spotify catalog.
    search_type can be a single type ('track') or comma-separated ('track,album,playlist').
    limit controls how many results come back per type (max 50).
    """
    return sp.search(q=query, type=search_type, limit=limit)

if __name__ == "__main__":
    import json

    track = get_current_track()
    print(json.dumps(track, indent=2))