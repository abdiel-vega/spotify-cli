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
    """
    go to the previous track.  if we are on the first track of the context
    (album / playlist) Spotify returns 403 — there is nothing before track 1.
    in that case we restart the current track from 0:00, which is the standard
    behavior of every music player when you press previous on the first song.
    """
    try:
        sp.previous_track()
    except Exception:
        # 403 "Restriction violated" → we're at the start of the context.
        # seek to the beginning of the current track instead.
        sp.seek_track(0)

def set_volume(level: int):
    sp.volume(level) # volume must be between 0 - 100

def toggle_shuffle(state: bool):
    sp.shuffle(state) # true = shuffle on | false = shuffle off

def toggle_repeat(mode: str):
    sp.repeat(mode) # options: 'track' | 'context' (album/playlist) | 'off'

def play_uri(track_uri: str):
    sp.start_playback(uris=[track_uri]) # track_uri looks like "spotify:track:4iV5W9uYEdYUVa79Axb7Rh"

def play_context_uri(context_uri: str):
    """play an album or playlist by its context URI."""
    sp.start_playback(context_uri=context_uri) # e.g. "spotify:album:..." or "spotify:playlist:..."

def play_track_in_context(track_uri: str):
    """
    play a track within its album context so that:
    - next / previous commands work correctly
    - playback continues after the track ends (autoplay)

    Spotify's /me/player/previous returns 403 when a track was started
    with uris=[...] because there is no surrounding context.  using the
    album as context_uri and the track as the offset fixes this.
    """
    track_id = track_uri.split(":")[-1]
    track_info = sp.track(track_id)
    album_uri = track_info["album"]["uri"]
    sp.start_playback(context_uri=album_uri, offset={"uri": track_uri})


# --- now playing ---

def get_current_track():
    """
    returns the full playback state from Spotify.
    the rest of the app will pull what's needed from this source.
    """
    return sp.current_playback()


# --- search ---
def search(query: str, search_type: str = "track", limit: int = 10):
    """
    searches the Spotify catalog.
    search_type can be a single type ('track') or comma-separated ('track,album,playlist').
    limit controls how many results come back per type (max 50).
    """
    return sp.search(q=query, type=search_type, limit=limit)

if __name__ == "__main__":
    import json

    track = get_current_track()
    print(json.dumps(track, indent=2))