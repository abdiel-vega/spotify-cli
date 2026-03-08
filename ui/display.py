from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.align import Align 
import time

from api.spotify_client import get_current_track
from ui.ascii_art import get_ascii_art

console = Console(force_terminal=True, color_system="truecolor")

def build_commands_panel() -> Text:
    """
    builds the commands reference strip at the bottom of the display.
    each command key is highlighted in green so it's immediately obvious
    what to type. this panel is static, it doesn't change each refresh.
    """
    return Text.assemble(
        ("  p", "bold green"),  (" play/pause    ", "dim"),
        ("n", "bold green"),    (" next track    ", "dim"),
        ("b", "bold green"),    (" previous track    ", "dim"),
        ("v ", "bold green"),   ("<0–100>", "bold green"), ("  set volume    ", "dim"),
        ("s ", "bold green"),   ("<query>", "bold green"), ("  search tracks    ", "dim"),
        ("q", "bold red"),      ("  quit", "dim"),
        justify="center",
    )

def format_duration(ms: int) -> str:
    """Converts milliseconds to MM:SS format"""
    seconds = ms // 1000
    minutes = seconds // 60
    remaining = seconds % 60
    return f"{minutes}:{remaining:02d}"


def build_display(data: dict) -> Layout:
    """
    Takes the raw Spotify playback dict and builds a display panel
    containing track metadata. This function is called every second
    by the Live display loop below.
    """
    # --- pull data from the playback dict ---
    song_name   = data.get("item", {}).get("name", "unknown")
    artists     = data.get("item", {}).get("artists", [])
    artist_str  = ", ".join([a.get('name', '') for a in artists])
    album       = data.get('item', {}).get('album', {})
    album_name  = album.get('name', 'unknown')
    release_yr  = album.get('release_date', '????')[:4]
    progress_ms = data.get('progress_ms', 0)
    duration_ms = data.get('item', {}).get('duration_ms', 0)
    is_playing  = data.get('is_playing', False)
    image_url   = album.get("images", [{}])[0].get("url", None)

    # --- build metadata panel (top) ---
    # format the progress as a fraction of total duration (0.0 - 1.0)
    # Rich Progress Bar requires a float between 0.0 and 1.0
    progress_pct = (progress_ms / duration_ms * 100) if duration_ms > 0 else 0

    # build progress bar as Text segments
    bar_width  = 30
    filled     = int(bar_width * progress_pct / 100)
    play_icon  = "▶  " if is_playing else "⏸  "
    play_color = "green" if is_playing else "yellow"

    # compose the display
    # Text.assemble builds a styled string piece by piece
    info_content = Text.assemble(
        ("\n\n\n", ""),
        (f"{song_name}\n", "bold white"),
        (f"{artist_str}\n", "green"),
        (f"{album_name} ({release_yr})\n\n", "dim"),
        ("█" * filled, "green"),
        ("░" * (bar_width - filled), "dim"),
        ("\n\n", ""),
        (play_icon, play_color),
        (f"{format_duration(progress_ms)} / {format_duration(duration_ms)}", "green"),
        justify="left",
    )

    # --- build ascii art panel (bottom) ---
    if image_url:
        # get_ascii_art returns raw ANSI string
        # Text.from_ansi() tells Rich to preserve existing color codes rather than treating them as Rich markup or plain text
        art_string = get_ascii_art(image_url, columns=64)
        art_content = Text.from_ansi(art_string)
    else:
        art_content = Text("No album art available", style="dim")
    
    # --- build the Layout and assign each panel to a region ---
    # the root is split into two rows: main content (ratio=10) and
    # a thin commands strip at the bottom (ratio=1).
    # the main content row is then split into the art/spacer/info columns
    layout = Layout()
    layout.split_column(
        Layout(name="main", ratio=10),
        Layout(name="commands", ratio=1),
    )
    
    layout["main"].split_row(
        Layout(Align.right(art_content, vertical="middle"), name="art", ratio=10),
        Layout(Text(" "), name="spacer", ratio=1),
        Layout(Align.left(info_content, vertical="middle"), name="info", ratio=10),
    )

    # assign the commands panel to the bottom strip
    layout["commands"].update(Align.center(build_commands_panel(), vertical="middle"))

    return layout
    

def show_now_playing():
    """
    Main display loop. Pulls Spotify every second and refreshes the layout.
    """
    # refresh_per_second=1 means the callback below runs every second
    with Live(console=console, refresh_per_second=1) as live:
        try:
            while True:
                data = get_current_track()

                if data is None:
                    # nothing is playing
                    live.update(Panel("[yellow]Now active playback detected.[/yellow]\nOpen Spotify and play something!",
                        border_style="yellow"))
                else:
                    # build and display the panel
                    live.update(build_display(data))

                time.sleep(1) # wait one second before pulling Spotify again

        except KeyboardInterrupt: # when Ctrl+C is pressed, we catch it here instead of letting
            console.print("\n[dim]Stopped.[/dim]")


if __name__ == "__main__":
    show_now_playing()