import click
import threading
import queue
import sys
import time

from rich.live import Live
from rich.panel import Panel

from api.spotify_client import (
    play, pause, next_track, previous_track,
    set_volume, toggle_shuffle, toggle_repeat,
    search, play_uri, get_current_track,
)
from ui.display import build_display, console


def process_command(cmd: str):
    """
    parses a single command string typed by the user and calls
    the appropriate spotify_client function.

    commands are intentionally single-key to keep them fast to type:
      p         → toggle play/pause
      n         → next track
      b         → previous track
      v <0-100> → set volume
      s <query> → search tracks
      q         → quit (raises KeyboardInterrupt to exit the Live loop)
    """
    parts = cmd.strip().lower().split()
    if not parts:
        return

    action = parts[0]

    if action == "p":
        # check current state and toggle accordingly
        data = get_current_track()
        if data and data.get("is_playing"):
            pause()
        else:
            play()

    elif action == "n":
        next_track()

    elif action == "b":
        previous_track()

    elif action == "v":
        if len(parts) < 2:
            return
        try:
            level = int(parts[1])
            if 0 <= level <= 100:
                set_volume(level)
        except ValueError:
            pass  # ignore non-integer input silently

    elif action == "s":
        if len(parts) < 2:
            return
        query = " ".join(parts[1:])
        results = search(query, search_type="track", limit=5)
        items = results.get("tracks", {}).get("items", [])
        if not items:
            return
        # print results below the live display area after it exits
        console.print(f"\n[bold]Results for '{query}':[/bold]")
        for i, item in enumerate(items):
            artist = ", ".join([a["name"] for a in item.get("artists", [])])
            console.print(f"  [[bold green]{i+1}[/bold green]] {item['name']} — {artist}")
        try:
            raw = input("\nEnter number to play (0 to cancel): ").strip()
            choice = int(raw)
            if 1 <= choice <= len(items):
                play_uri(items[choice - 1]["uri"])
        except (ValueError, EOFError):
            pass

    elif action == "q":
        # raising keyboardinterrupt from inside the thread won't stop the
        # main thread, so we use a flag instead — see run_interactive() below.
        raise SystemExit


@click.group()
def cli():
    """🎵 Spotify Terminal CLI — Control Spotify from your terminal."""
    pass


@cli.command("run")
def run_cmd():
    """
    Launch the interactive Spotify CLI.
    Displays now-playing info and accepts commands typed below the UI.
    """
    # thread-safe queue passes typed commands from the input thread
    # to the main display loop without blocking the live refresh.
    cmd_queue   = queue.Queue()
    stop_event  = threading.Event()

    def input_listener():
        """
        Runs in a background daemon thread. Reads lines from stdin and
        drops them into the queue for the main loop to process.
        Daemon=True means this thread dies automatically when the main
        thread exits — no manual cleanup needed.
        """
        while not stop_event.is_set():
            try:
                line = sys.stdin.readline()
                if line:
                    cmd_queue.put(line.strip())
            except Exception:
                break

    listener = threading.Thread(target=input_listener, daemon=True)
    listener.start()

    with Live(console=console, refresh_per_second=1) as live:
        try:
            while True:
                data = get_current_track()
                if data is None:
                    live.update(Panel(
                        "[yellow]No active playback detected.[/yellow]\nOpen Spotify and play something!",
                        border_style="yellow"
                    ))
                else:
                    live.update(build_display(data))

                # drain the command queue, process everything typed
                # since the last refresh before sleeping again.
                while not cmd_queue.empty():
                    cmd = cmd_queue.get()
                    try:
                        process_command(cmd)
                    except SystemExit:
                        stop_event.set()
                        raise KeyboardInterrupt

                time.sleep(1)

        except KeyboardInterrupt:
            stop_event.set()
            console.print("\n[dim]Stopped.[/dim]")


# --- commands ---

@cli.command("play")
def play_cmd():
    """Resume playback."""
    play()
    click.echo("▶  Playback resumed.")

@cli.command("pause")
def pause_cmd():
    """Pause playback."""
    pause()
    click.echo("⏸  Playback paused.")

@cli.command("next")
def next_cmd():
    """Skip to next track."""
    next_track()
    click.echo("⏭  Skipped to next track.")

@cli.command("previous")
def previous_cmd():
    """Go back to previous track."""
    previous_track()
    click.echo("⏮  Previous track.")

@cli.command("volume")
@click.argument("level", type=click.IntRange(0, 100))
def volume_cmd(level):
    """Set volume level (0–100)."""
    set_volume(level)
    click.echo(f"🔊  Volume set to {level}%.")

@cli.command("shuffle")
@click.option("--on",  "state", flag_value=True,  default=True, help="Turn shuffle on")
@click.option("--off", "state", flag_value=False,               help="Turn shuffle off")
def shuffle_cmd(state):
    """Toggle shuffle on or off."""
    toggle_shuffle(state)
    click.echo(f"🔀  Shuffle {'on' if state else 'off'}.")

@cli.command("repeat")
@click.argument("mode", type=click.Choice(["track", "context", "off"]))
def repeat_cmd(mode):
    """Set repeat mode: track | context | off."""
    toggle_repeat(mode)
    click.echo(f"🔁  Repeat set to '{mode}'.")

@cli.command("search")
@click.argument("query")
@click.option("--type", "search_type",
              type=click.Choice(["track", "artist", "album", "playlist"]),
              default="track", help="Type of content to search for.")
@click.option("--limit", default=10, help="Number of results (max 50).")
def search_cmd(query, search_type, limit):
    """Search Spotify for tracks, artists, albums, or playlists."""
    results = search(query, search_type=search_type, limit=limit)
    items   = results.get(search_type + "s", {}).get("items", [])
    if not items:
        click.echo("No results found.")
        return
    click.echo(f"\nResults for '{query}':\n")
    for i, item in enumerate(items):
        name = item.get("name", "Unknown")
        if search_type == "track":
            artists = ", ".join([a["name"] for a in item.get("artists", [])])
            click.echo(f"  [{i+1}] {name} — {artists}")
        else:
            click.echo(f"  [{i+1}] {name}")
    if search_type == "track":
        choice = click.prompt("\nEnter number to play (0 to cancel)", type=int, default=0)
        if 1 <= choice <= len(items):
            play_uri(items[choice - 1]["uri"])
            click.echo(f"▶  Now playing: {items[choice - 1]['name']}")


if __name__ == "__main__":
    cli()