import click
from api.spotify_client import (
    play, pause, next_track, previous_track,
    set_volume, toggle_shuffle, toggle_repeat,
    search, play_uri
)
from ui.display import show_now_playing
# click.group() turns the 'cli' funciotn into the root container for all commands

@click.group()
def cli():
    """Spotify CLI - Control Spotify from the terminal"""
    pass

# --- now playing ---
@cli.command("now-playing")
def now_playing_cmd():
    """Display the current playing track."""
    show_now_playing()

# --- playback controls ---
# each of these is a thin wrapper - Click handles the CLI interface
# spotify_client functions handle the actual Spotify API call
@cli.command("play")
def play_cmd():
    """Resume playback."""
    play()
    click.echo("▶ Playback resumed")

@cli.command("pause")
def pause_cmd():
    """Pause playback."""
    pause()
    click.echo("⏸ Playback paused")

@cli.command("next")
def next_cmd():
    """Skip to next track."""
    next_track()
    click.echo("⏭ Skipped to next track")

@cli.command("previous")
def previous_cmd():
    """Go back to previous track."""
    previous_track()
    click.echo("⏮ Went back to previous track")

@cli.command("volume")
# click.argument is for positional inputs. the user types the value directly after the command name
@click.argument("level", type=click.IntRange(0, 100))
def volume_cmd(level):
    """Set volume level (0-100)."""
    set_volume(level)
    click.echo(f"🔊 Volume set to {level}%")

@cli.command("shuffle")
# click.option is for named flags. the user types --on or --off
@click.option("--on", "state", flag_value=True, default=True, help="Turn shuffle on")
@click.option("--off", "state", flag_value=False, help="Turn shuffle off")
def shuffle_cmd(state):
    """Toggle shuffle on/off."""
    toggle_shuffle(state)
    label = "on" if state else "off"
    click.echo(f"🔀 Shuffle {label}")

@cli.command("repeat")
# click.Choice is to restrict the input to only valid options
# Click shows an error if user types anything else
@click.argument("mode", type=click.Choice(["track", "context", "off"]))
def repeat_cmd(mode):
    """Set repeat mode: track | context (album/playlist) | off"""
    toggle_repeat(mode)
    click.echo(f"🔂 Repeat set to {mode}")

# --- search ---
@cli.command("search")
@click.argument("query")
# the type parameter here uses Click's Choice to restrict to valid Spotify search types
# default="track" means if the user doesn't pass --type, it searches tracks
@click.option("--type", "search_type",
    type=click.Choice(["track", "album", "artist", "playlist"]),
    default="track",
    help="Type of content to search for")
@click.option("--limit", default=10, help="Number of results to show (max 50).")
def search_cmd(query, search_type, limit):
    """Search Spotify for tracks, albums, artists, or playlists."""
    results = search(query, search_type=search_type, limit=limit)
    items = results.get(search_type + "s", {}).get("items", [])

    if not items:
        click.echo("No results found.")
        return

    # display results as a numbered list
    click.echo(f"\nResults for '{query}':\n")
    for i, item in enumerate(items):
        name = item.get("name", "Unknown")
        # for tracks, also show the artist name besides title
        if search_type == "track":
            artists = ", ".join([a["name"] for a in item.get("artists", [])])
            click.echo(f" [{i+1}] {name} - {artists}")
        else:
            click.echo(f" [{i+1}] {name}")

    # pick song user prompt after search results
    if search_type == "track":
        choice = click.prompt("\nEnter number to play (or 0 to cancel)", type=int, default=0)
        if 1 <= choice <= len(items):
            uri = items[choice - 1]["uri"]
            play_uri(uri)
            click.echo(f"▶ Playing: {items[choice - 1]['name']}")

if __name__ == "__main__":
    cli()