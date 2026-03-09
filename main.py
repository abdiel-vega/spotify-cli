import click
import threading
import queue
import time
import msvcrt

from rich.live import Live
from rich.panel import Panel

from api.spotify_client import (
    play, pause, next_track, previous_track,
    set_volume, toggle_shuffle, toggle_repeat,
    search, play_uri, play_context_uri, get_current_track,
)
from ui.display import build_display, console


# single-character commands that execute the moment the key is pressed.
# no enter required = instant feedback
INSTANT_COMMANDS = {'p', 'n', 'b', 'f', 'r', 'q'}

# shared state dict, both the input thread and display loop read-write this
# using a dict (mutable) means the thread can update values in-place and
# the main loop sees the changes without any extra sync needed
state = {
    "search_results": None, # list of track dicts when search is active, None otherwise
    "search_query": "", # the query string
}

def process_command(cmd: str) -> bool:
    """
    Parses and executes a command string.
    Returns True if the app should quit, False otherwise.
    """
    parts = cmd.strip().lower().split()
    if not parts:
        return False

    action = parts[0]

    if action == "p":
        data = get_current_track()
        if data and data.get("is_playing"):
            pause()
        else:
            play()

    elif action == "n":
        next_track()
        state["search_results"] = None # clear results on track change

    elif action == "b":
        previous_track()
        state["search_results"] = None # clear results on track change

    elif action == "f":
        data = get_current_track()
        current_shuffle = data.get("shuffle_state", False) if data else False
        toggle_shuffle(not current_shuffle)

    elif action == "r":
        # cycle: off → context → track → off
        REPEAT_CYCLE = {"off": "context", "context": "track", "track": "off"}
        data = get_current_track()
        current_repeat = data.get("repeat_state", "off") if data else "off"
        next_mode = REPEAT_CYCLE.get(current_repeat, "off")
        toggle_repeat(next_mode)

    elif action == "v":
        if len(parts) >= 2:
            try:
                level = int(parts[1])
                if 0 <= level <= 100:
                    set_volume(level)
            except ValueError:
                pass

    elif action == "s":
        if len(parts) >= 2:
            query   = " ".join(parts[1:])
            # search for tracks, albums, and playlists at once
            results = search(query, search_type="track,album,playlist", limit=5)

            # build a unified, flat list with type metadata
            unified = []

            for track in results.get("tracks", {}).get("items", []):
                if track is None:
                    continue
                artists = ", ".join(a["name"] for a in track.get("artists", []))
                unified.append({
                    "name":     track["name"],
                    "subtitle": artists,
                    "uri":      track["uri"],
                    "type":     "track",
                })

            for album in results.get("albums", {}).get("items", []):
                if album is None:
                    continue
                artists = ", ".join(a["name"] for a in album.get("artists", []))
                unified.append({
                    "name":     album["name"],
                    "subtitle": artists,
                    "uri":      album["uri"],
                    "type":     "album",
                })

            for pl in results.get("playlists", {}).get("items", []):
                if pl is None:
                    continue
                owner = (pl.get("owner") or {}).get("display_name", "Unknown")
                unified.append({
                    "name":     pl["name"],
                    "subtitle": f"by {owner}",
                    "uri":      pl["uri"],
                    "type":     "playlist",
                })

            state["search_results"] = unified
            state["search_query"]   = query

    elif action == "c":
        # clear search results and return to now-playing view
        state["search_results"] = None

    elif action == "q":
        return True  # signal the main loop to exit

    else:
        # if search results are showing and user types a number, play that result
        if state["search_results"] is not None:
            try:
                choice = int(action)
                items  = state["search_results"]
                if 1 <= choice <= len(items):
                    selected = items[choice - 1]
                    if selected["type"] == "track":
                        play_uri(selected["uri"])
                    else:
                        # albums and playlists need context_uri
                        play_context_uri(selected["uri"])
                    state["search_results"] = None  # close results after playing
            except ValueError:
                pass

    return False


@click.group()
def cli():
    """Spotify Terminal CLI"""
    pass


@cli.command("run")
def run_cmd():
    """Launch the interactive Spotify CLI."""

    cmd_queue    = queue.Queue()   # completed commands ready to execute
    buffer_ref   = [""]            # mutable string holding what's being typed
    stop_event   = threading.Event()

    def input_listener():
        """
        Background thread — reads keypresses one character at a time using
        msvcrt.getwch() which returns immediately on any keypress with no
        need for Enter. Builds a buffer for multi-character commands (v, s)
        and sends completed commands to cmd_queue.
        """
        buf = ""
        while not stop_event.is_set():
            if msvcrt.kbhit():
                # getwch() reads one character immediately without echoing it
                # to the terminal — we control display ourselves via the input line
                ch = msvcrt.getwch()

                # special / extended keys (arrows, function keys, mouse
                # scroll) send a two-byte sequence: a prefix (\x00 or
                # \xe0) followed by a scancode.  Consume both and ignore.
                if ch in ('\x00', '\xe0'):
                    msvcrt.getwch()  # eat the scancode
                    continue

                if ch in ('\r', '\n'):
                    # [Enter] submit whatever is in the buffer
                    if buf:
                        cmd_queue.put(buf)
                        buf = ""
                        buffer_ref[0] = ""

                elif ch == '\x08':
                    # [Backspace] remove last character from buffer
                    buf = buf[:-1]
                    buffer_ref[0] = buf

                elif ch == '\x03':
                    # [Ctrl+C] treat as quit
                    cmd_queue.put("q")

                elif ch in INSTANT_COMMANDS and buf == "" and state["search_results"] is None:
                    # single-key instant commands only fire when:
                    # - buffer is empty (not mid-word)
                    # - search results are not showing (so numbers go to track selection)
                    cmd_queue.put(ch)

                else:
                    buf += ch
                    buffer_ref[0] = buf

            time.sleep(0.02)  # 20ms poll — fast enough to feel instant

    listener = threading.Thread(target=input_listener, daemon=True)
    listener.start()

    # screen=True is the key fix for flickering:
    # it switches to the terminal's alternate screen buffer, so Rich
    # renders in-place rather than clearing and reprinting each refresh.
    # The original terminal content is restored when the Live block exits.
    with Live(console=console, refresh_per_second=4, screen=True) as live:
        try:
            cached_data = None  # cache last good Spotify response

            while True:
                # Fetch fresh data — fall back to cache if request fails
                try:
                    data = get_current_track()
                    if data:
                        cached_data = data
                except Exception:
                    data = cached_data

                if data is None:
                    live.update(Panel(
                        "[yellow]No active playback detected.[/yellow]\n"
                        "Open Spotify and play something!",
                        border_style="yellow"
                    ))
                else:
                    # Pass the current input buffer so the display shows
                    # what the user is typing without it being lost on refresh
                    live.update(build_display(
                        data,
                        input_buffer=buffer_ref[0],
                        search_results=state["search_results"],
                        search_query=state["search_query"],
                    ))

                # Process any completed commands
                while not cmd_queue.empty():
                    cmd = cmd_queue.get()
                    should_quit = process_command(cmd)
                    if should_quit:
                        stop_event.set()
                        raise KeyboardInterrupt

                time.sleep(0.25)  # 4 refreshes/sec feels smooth without hammering the API

        except KeyboardInterrupt:
            stop_event.set()


# --- Standalone commands (still usable for scripting/hotkeys) ---

@cli.command("play")
def play_cmd():
    play()
    click.echo("▶  Playback resumed.")

@cli.command("pause")
def pause_cmd():
    pause()
    click.echo("⏸  Playback paused.")

@cli.command("next")
def next_cmd():
    next_track()
    click.echo("⏭  Skipped to next track.")

@cli.command("previous")
def previous_cmd():
    previous_track()
    click.echo("⏮  Previous track.")

@cli.command("volume")
@click.argument("level", type=click.IntRange(0, 100))
def volume_cmd(level):
    set_volume(level)
    click.echo(f"🔊  Volume set to {level}%.")

@cli.command("shuffle")
@click.option("--on",  "state", flag_value=True,  default=True)
@click.option("--off", "state", flag_value=False)
def shuffle_cmd(state):
    toggle_shuffle(state)
    click.echo(f"🔀  Shuffle {'on' if state else 'off'}.")

@cli.command("repeat")
@click.argument("mode", type=click.Choice(["track", "context", "off"]))
def repeat_cmd(mode):
    toggle_repeat(mode)
    click.echo(f"🔁  Repeat set to '{mode}'.")

@cli.command("search")
@click.argument("query")
@click.option("--type", "search_type",
              type=click.Choice(["track", "artist", "album", "playlist", "all"]),
              default="all")
@click.option("--limit", default=5)
def search_cmd(query, search_type, limit):
    # when "all", search tracks + albums + playlists at once
    if search_type == "all":
        api_type = "track,album,playlist"
    else:
        api_type = search_type

    results = search(query, search_type=api_type, limit=limit)

    # build a unified numbered list
    unified = []
    TYPE_LABELS = {
        "track":    "🎵 Track",
        "album":    "💿 Album",
        "playlist": "📋 Playlist",
        "artist":   "🎤 Artist",
    }

    for stype in api_type.split(","):
        for item in results.get(stype + "s", {}).get("items", []):
            name = item.get("name", "Unknown")
            if stype in ("track", "album"):
                subtitle = ", ".join(a["name"] for a in item.get("artists", []))
            elif stype == "playlist":
                subtitle = f"by {item.get('owner', {}).get('display_name', 'Unknown')}"
            else:
                subtitle = ""
            unified.append({
                "name": name, "subtitle": subtitle,
                "uri": item["uri"], "type": stype,
            })

    if not unified:
        click.echo("No results found.")
        return

    click.echo(f"\nResults for '{query}':\n")
    for i, entry in enumerate(unified):
        label = TYPE_LABELS.get(entry["type"], "")
        click.echo(f"  [{i+1:>2}] {label}  {entry['name']} — {entry['subtitle']}")

    choice = click.prompt("\nEnter number to play (0 to cancel)", type=int, default=0)
    if 1 <= choice <= len(unified):
        selected = unified[choice - 1]
        if selected["type"] == "track":
            play_uri(selected["uri"])
        else:
            play_context_uri(selected["uri"])
        click.echo(f"▶  Now playing: {selected['name']}")


if __name__ == "__main__":
    cli()