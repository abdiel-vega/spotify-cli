<p align="center">
  <img src="https://upload.wikimedia.org/wikipedia/commons/8/84/Spotify_icon.svg" alt="Spotify Logo" width="80"/>
</p>

<h1 align="center">Spotify CLI</h1>

<p align="center">
  <em>simple spotify terminal cli built with python</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+"/>
  <img src="https://img.shields.io/badge/platform-Windows-0078D6?style=flat-square&logo=windows&logoColor=white" alt="Windows"/>
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="MIT License"/>
</p>

---

## introduction

This project is a **Python-based command-line interface** that lets you control **Spotify playback**, search the catalog, and view the current playing song's album art all without leaving your terminal. It connects to your Spotify account via the Web API and renders a live, auto-refreshing dashboard with full-color ASCII album art, real-time track progress, and single-keypress controls.

The interface is built on Rich's alternate screen buffer for flicker-free rendering and uses a threaded input listener (`msvcrt`) to capture keypresses instantly, which means no Enter key required for common actions.

---

## project structure

```
spotify-cli/
├── main.py                  # entry point - CLI commands & interactive loop
├── api/
│   └── spotify_client.py    # thin wrapper around spotipy for playback/search
├── auth/
│   └── spotify_auth.py      # OAuth2 (PKCE) setup via SpotifyOAuth
├── ui/
│   ├── display.py           # Rich layout builder — now-playing & search views
│   └── ascii_art.py         # album cover → half-block ANSI art converter
├── requirements.txt
├── .env                     # spotify credentials (git-ignored)
└── .gitignore
```

---

## How the Dependencies Work

| Package           | Role                                                                                                                                          |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| **spotipy**       | Authenticates with Spotify via OAuth 2.0 and wraps every Web API endpoint (playback, search, library) into simple Python methods.             |
| **rich**          | Powers the live terminal UI: `Layout`, `Panel`, `Text`, and `Live` provide flicker-free, full-color rendering on the alternate screen buffer. |
| **click**         | Defines the CLI command group (`run`, `play`, `pause`, `search`, etc.) with argument parsing and type validation.                             |
| **Pillow**        | Opens and resizes album art images in memory so they can be converted pixel-by-pixel into ANSI color codes.                                   |
| **requests**      | Downloads album cover images from Spotify's CDN for the ASCII art renderer.                                                                   |
| **python-dotenv** | Loads `SPOTIPY_CLIENT_ID`, `SPOTIPY_CLIENT_SECRET`, and `SPOTIPY_REDIRECT_URI` from the `.env` file at startup.                               |
| **ascii-magic**   | Bundled as a reference utility for ASCII art conversion (the project uses a custom half-block renderer for higher fidelity).                  |

---

## quick setup

### 1 · create a Spotify App

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
2. Click **Create App**.
3. Set the **Redirect URI** to `http://127.0.0.1:8888/callback`.
4. Note your **Client ID** and **Client Secret**.

### 2 · clone & configure

```bash
git clone https://github.com/<your-username>/spotify-cli.git
cd spotify-cli
```

Create a `.env` file in the project root:

```env
SPOTIPY_CLIENT_ID=your_client_id_here
SPOTIPY_CLIENT_SECRET=your_client_secret_here
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

### 3 · set up python virtual vnvironment (venv)

```bash
# create and activate a venv
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# install dependencies
pip install -r requirements.txt
```

### 4 · authenticate & launch

```bash
# first run opens a browser for Spotify login (token is cached after that)
python main.py run
```

> **note:** Spotify requires an active playback session on at least one device. Open the Spotify desktop or mobile app and start playing something before launching the CLI.

---

## feature showcase

### live ASCII album art

Album covers are downloaded and rendered in **true-color ANSI** using the Unicode half-block character (`▀`). Each terminal character encodes two pixel rows, foreground for the top pixel, and background for the bottom, doubling the effective resolution. Results are LRU-cached so art only re-renders on track change.

### real-time now playing

The dashboard auto-refreshes 4 times per second, showing:
- **Track name**, **artist(s)**, and **album**
- A **progress bar** with elapsed / total duration
- Current **play / pause** state indicator

### instant keyboard controls

Single-keypress commands execute the moment you press the key, no Enter needed:

| Key | Action                                          |
| --- | ----------------------------------------------- |
| `p` | Toggle play / pause                             |
| `n` | Skip to next track                              |
| `b` | Go to previous track                            |
| `f` | Toggle shuffle on / off                         |
| `r` | Cycle repeat mode (off → context → track → off) |
| `q` | Quit the CLI                                    |

Multi-character commands (press Enter to submit):

| Command | Action |
|---------|--------|
| `v <0-100>` | Set volume to a specific percentage |
| `s <query>` | Search for tracks, albums, and playlists |
| `c` | Clear search results and return to now-playing view |

### unified search

Type `s <query>` to search across **tracks**, **albums**, and **playlists** simultaneously. Results are displayed as a numbered list with color-coded type badges. Enter the result number to start playback immediately.

### standalone Commands

Every action is also available as a one-shot CLI command for scripting or quick use:

```bash
python main.py play
python main.py pause
python main.py next
python main.py previous
python main.py volume 75
python main.py shuffle --on
python main.py repeat track
python main.py search "Daft Punk" --type all --limit 10
```

---

## required Spotify scopes

The app requests only the permissions it needs:

| Scope | Purpose |
|-------|---------|
| `user-read-playback-state` | Read current track, progress, shuffle/repeat state |
| `user-modify-playback-state` | Play, pause, skip, set volume, toggle shuffle/repeat |
| `user-read-currently-playing` | Get the currently playing track |
| `playlist-read-private` | Access private playlists in search results |
| `user-library-read` | Read saved library data |

---

<p align="center">
  <sub>Built with <a href="https://spotipy.readthedocs.io/">Spotipy</a> · <a href="https://rich.readthedocs.io/">Rich</a> · <a href="https://click.palletsprojects.com/">Click</a></sub>
</p>
