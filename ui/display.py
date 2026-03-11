from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.align import Align 
import re
import time

from api.spotify_client import get_current_track
from ui.ascii_art import get_ascii_art

console = Console(force_terminal=True, color_system="truecolor")

# regex to match emoji and other problematic wide Unicode characters
# these cause Rich's layout to miscalculate column widths, leading to flicker
_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"  # dingbats
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols extended-A
    "\U00002600-\U000026FF"  # misc symbols
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U0000200D"             # zero-width joiner
    "\U000020E3"             # combining enclosing keycap
    "\U0000E000-\U0000F8FF"  # private use area
    "]+"
)

def strip_emojis(text: str) -> str:
    """remove emoji characters that cause terminal width miscalculations."""
    return _EMOJI_RE.sub("", text).strip()

def build_commands_panel(search_active: bool = False, result_count: int = 0) -> Text:
    """
    commands strip changes when search results are showing
    numbers select a track, Esc or c clears results
    """
    if search_active:
        max_num = str(result_count) if result_count > 0 else "?"
        return Text.assemble(
            (f"<1-{max_num}>", "bold green"),  (" play result    ", "dim"),
            ("c", "bold yellow"),     (" clear results    ", "dim"),
            ("q", "bold red"),        ("  quit", "dim"),
            justify="center",
        )
    return Text.assemble(
        ("p", "bold green"),  (" play/pause    ", "dim"),
        ("n", "bold green"),  (" next    ", "dim"),
        ("b", "bold green"),  (" previous    ", "dim"),
        ("f", "bold green"),  (" shuffle    ", "dim"),
        ("r", "bold green"),  (" repeat    ", "dim"),
        ("v", "bold green"), (" <0-100>", "bold green"), (" volume    ", "dim"),
        ("s", "bold green"), (" <query>", "bold green"), (" search    ", "dim"),
        ("q", "bold red"),    (" quit", "dim"),
        justify="center",
    )

def format_duration(ms: int) -> str:
    """converts milliseconds to MM:SS format"""
    seconds = ms // 1000
    minutes = seconds // 60
    remaining = seconds % 60
    return f"{minutes}:{remaining:02d}"


def build_display(data: dict, input_buffer: str = "", search_results=None, search_query: str = "") -> Layout:
    """
    takes the raw Spotify playback dict and builds a display panel
    containing track metadata. this function is called every second
    by the live display loop below.
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

    # --- right panel: search results or track info ---
    if search_results is not None:
        # search results view, replaces the track info panel
        if len(search_results) == 0:
            right_content = Text.assemble(
                ("\n\n\n", ""),
                (f'No results for "{search_query}"', "dim"),
                justify="left",
            )
        else:
            # build a numbered list of results grouped with type badges
            # 32-line budget: 3 lines header + 2 lines per result → max 14 results
            MAX_VISIBLE = 14
            TYPE_BADGES = {
                "track":    ("Track",    "green"),
                "album":    ("Album",    "cyan"),
                "playlist": ("Playlist", "magenta"),
            }
            parts = [
                (f' Results for "{search_query}"\n\n', "bold white"),
            ]
            visible = search_results[:MAX_VISIBLE]
            for i, item in enumerate(visible):
                badge_text, badge_style = TYPE_BADGES.get(item["type"], ("?", "dim"))
                name = strip_emojis(item['name'])
                name = name if len(name) <= 46 else name[:45] + "…"
                subtitle = strip_emojis(item['subtitle'])
                subtitle = subtitle if len(subtitle) <= 46 else subtitle[:45] + "…"
                parts += [
                    (f" {i+1:>2} ", "bold green"),
                    (f"[{badge_text}] ", badge_style),
                    (f"{name}\n", "white"),
                    (f"     {subtitle}\n", "dim"),
                ]
            # show truncation notice if results were clipped
            hidden = len(search_results) - len(visible)
            if hidden > 0:
                parts.append((f"\n     … and {hidden} more result{'s' if hidden != 1 else ''}\n", "dim"))
            right_content = Text.assemble(*parts, justify="left")

    else:
        # normal now-playing info view
        right_content = Text.assemble(
            ("\n\n\n", ""),
            (f"{song_name}\n", "bold white"),
            (f"{artist_str}\n", "green"),
            (f"{album_name}\n\n", "dim"),
            ("█" * filled, "green"),
            ("░" * (bar_width - filled), "dim"),
            ("\n\n", ""),
            (play_icon, play_color),
            (f"{format_duration(progress_ms)} / {format_duration(duration_ms)}", "white"),
            justify="left",
        )

    # --- build ascii art panel (bottom) ---
    if image_url:
        # get_ascii_art returns raw ANSI string
        # Text.from_ansi() tells Rich to preserve existing color codes rather than treating them as Rich markup or plain text
        art_content = Text.from_ansi(get_ascii_art(image_url, columns=64))
    else:
        art_content = Text("No album art available", style="dim")

    # --- input line ---
    input_line = Text.assemble(
        ("> ", "bold green"),
        (input_buffer, "white"),
        ("_", "white"),
    )
    
    # --- build the Layout and assign each panel to a region ---
    # the root is split into two rows: main content (ratio=10) and
    # a thin commands strip at the bottom (ratio=1)
    # the main content row is then split into the art/spacer/info columns
    layout = Layout()
    layout.split_column(
        Layout(name="main", ratio=10),
        Layout(name="commands", ratio=1),
        Layout(name="input", ratio=1),
    )

    layout["main"].split_row(
        Layout(Align.right(art_content, vertical="middle"), name="art", ratio=10),
        Layout(Text(" "), name="spacer", ratio=1),
        Layout(Align.left(right_content, vertical="middle"), name="info", ratio=10),
    )

    # assign the commands panel to the bottom strip
    result_count = len(search_results) if search_results else 0
    layout["commands"].update(
        Align.center(build_commands_panel(
            search_active=search_results is not None,
            result_count=result_count,
        ), vertical="middle")
    )
    layout["input"].update(Align.center(input_line, vertical="middle"))

    return layout
    

def show_now_playing():
    """
    Main display loop. Pulls Spotify every second and refreshes the layout.
    """
    # callback below runs every second
    with Live(console=console, refresh_per_second=1, screen=True) as live:
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

                time.sleep(0.25) # wait before pulling Spotify again

        except KeyboardInterrupt: # when Ctrl+C is pressed, we catch it here instead of letting
            pass


if __name__ == "__main__":
    show_now_playing()