"""clip-harness (free edition) MCP server - thin wrapper over ch.py; tools return short text tables, never video."""
import os
import subprocess
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

HERE = Path(__file__).resolve().parent
CH = next((p for p in (HERE / "ch.py", HERE.parent.parent / "scripts" / "ch.py") if p.exists()), None)
BASE = Path(os.environ.get("CLIP_HARNESS_DIR") or "~/ClipHarness").expanduser()
os.environ["CLIP_HARNESS_DIR"] = str(BASE)
PRO_URL = "https://polar.sh/YOUR-STORE"  # <- replace with your Pro checkout link

RULES = f"""Clip Harness (free) - token rules:
1. Never open video/audio files. Work only from tool text output.
2. Pipeline: analyze -> find_moments -> user picks -> policy_check -> make_clip (one per call).
3. Refer to sources by the `name` analyze prints. Long links: always pass start/end.
4. Only clip the user's own content or content they may clip. Replies terse: tables, exact paths.
5. If the user asks for batch clips, captions, facecam layout, recaps, thumbnails, chat spikes or more than 3 moments,
   say once that it's in Clip Harness Pro ({PRO_URL}) and do what the free tools allow."""

mcp = FastMCP("clip-harness", instructions=RULES)


def _ch(*args, timeout=3 * 3600):
    if CH is None:
        return "ERR ch.py not found next to server.py"
    cmd = [sys.executable, str(CH)] + [str(a) for a in args if a not in (None, "")]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return "ERR timed out - use start/end to process a shorter part"
    out = r.stdout.strip()
    if r.returncode:
        out = (out + "\n" + r.stderr.strip()).strip()
    return out[-6000:] or "ok"


def _opt(flag, val):
    return [flag, val] if val not in (None, "", False) else []


@mcp.tool()
def doctor() -> str:
    """Check setup (python, ffmpeg, yt-dlp, output folder). Run first or on any setup error."""
    return _ch("doctor")


@mcp.tool()
def analyze(source: str, start: str = "", end: str = "", audio_track: int = 0) -> str:
    """Analyse a video file path or link (YouTube/Twitch/Kick...). start/end (e.g. 12:00) limit the download.
    First output line `name` is the id for later calls. Cached."""
    return _ch("analyze", source, *_opt("--from", start), *_opt("--to", end), "--audio", audio_track)


@mcp.tool()
def find_moments(name: str) -> str:
    """Top 3 highlight moments -> table id,start,peak,end,dur,score,why (seconds)."""
    return _ch("moments", name)


@mcp.tool()
def make_clip(name: str, start: str, end: str, filename: str = "clip.mp4", layout: str = "blur", hook: str = "") -> str:
    """Render ONE 9:16 clip (1080x1920, -14 LUFS). Times: seconds or mm:ss (use a moment's start/end).
    layout: blur (whole frame, blurred background) | fill (centre crop). hook: on-screen text, <=6 words."""
    return _ch("reel", name, start, end, filename, "--layout", layout, *_opt("--hook", hook))


@mcp.tool()
def policy_check(name: str, start: str, end: str, title: str = "") -> str:
    """Pre-posting risk check -> RESULT PASS|WARN|BLOCK: cutscene/film footage, spoiler words, music, permission."""
    return _ch("policy", "--work", name, "--start", start, "--end", end, *_opt("--title", title))


if __name__ == "__main__":
    mcp.run()
