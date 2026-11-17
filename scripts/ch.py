#!/usr/bin/env python3
"""clip-harness (free edition) CLI: every heavy step runs here so Claude reads short TSV, not video.

Needs Python 3.9+ and ffmpeg (system, or pip-bundled imageio-ffmpeg). Optional: faster-whisper (captions).
Usage: python3 ch.py <command> [args]   (run with -h for each command)
"""
import argparse, json, math, os, re, shutil, statistics, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRO_URL = "https://polar.sh/YOUR-STORE"  # <- replace with your Pro checkout link
PRO = f"Pro feature - get Clip Harness Pro: {PRO_URL}"
NL = "\\N"  # ASS line break
FFQ = ["-hide_banner", "-loglevel", "error", "-nostdin", "-y"]


# ---------- helpers ----------
def die(msg, code=1):
    print(f"ERR {msg}", file=sys.stderr); sys.exit(code)


def ffbin():
    exe = os.environ.get("CH_FFMPEG") or shutil.which("ffmpeg")
    if not exe:
        try:
            import imageio_ffmpeg
            exe = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            exe = None
    return exe


FF = ffbin() or "ffmpeg"


def need(tool):
    if tool == "ffmpeg" and ffbin():
        return
    if not shutil.which(tool):
        die(f"{tool} not found. Install ffmpeg (macOS: brew install ffmpeg | Win: winget install ffmpeg | Linux: apt install ffmpeg)")


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        die(f"{cmd[0]} failed: {r.stderr.strip()[-600:]}")
    return r.stdout


def preset(name):
    p = Path(name)
    if not p.exists():
        p = ROOT / "presets" / f"{name}.json"
    if not p.exists():
        die(f"preset not found: {name}")
    return json.loads(p.read_text())


BASE = Path(os.environ.get("CLIP_HARNESS_DIR", "~/ClipHarness")).expanduser()


def workdir(src, base=None):
    w = (Path(base) if base else BASE) / Path(src).stem
    w.mkdir(parents=True, exist_ok=True)
    return w


def W(name):  # analysed name or path -> work dir
    p = Path(str(name)).expanduser()
    if (p / "probe.tsv").exists():
        return p
    return BASE / (p.stem if p.is_file() else p.name)


def SRC(name):  # video file path, or analysed name -> original video
    p = Path(str(name)).expanduser()
    if p.is_file():
        return p.resolve()
    pt = W(name) / "probe.tsv"
    if pt.exists():
        return Path(next(l.split("\t", 1)[1] for l in pt.read_text().splitlines() if l.startswith("src\t")))
    die(f"not a video file or analysed name: {name}")


def OUT(path, name):  # bare filename -> <work>/out/<file>
    p = Path(path).expanduser()
    return p.resolve() if p.is_absolute() or str(p.parent) != "." else (W(name) / "out" / p)


def fetch(url, frm=None, to=None):
    """Download a VOD/video link with yt-dlp (user's own or permitted content)."""
    dl = BASE / "_downloads"; dl.mkdir(parents=True, exist_ok=True)
    if shutil.which("yt-dlp"):
        ytd = ["yt-dlp"]
    else:
        try:
            import yt_dlp  # noqa: F401
            ytd = [sys.executable, "-m", "yt_dlp"]
        except ImportError:
            die("yt-dlp missing: pip install -U yt-dlp  (or brew install yt-dlp)")
    tag = f"-{int(parse_t(frm or 0))}-{int(parse_t(to)) if to else 'end'}" if (frm or to) else ""
    cmd = ytd + (["--ffmpeg-location", FF] if ffbin() else []) + ["-f", "bv*[height<=1080]+ba/b[height<=1080]/b", "--merge-output-format", "mp4", "--no-playlist",
                 "--quiet", "--no-warnings", "--print", "after_move:filepath",
                 "-o", str(dl / f"%(extractor)s-%(id)s{tag}.%(ext)s")]
    if frm or to:
        cmd += ["--download-sections", f"*{frm or 0}-{to or 'inf'}", "--force-keyframes-at-cuts"]
    t0 = time.time(); before = set(dl.glob("*.mp4"))
    outp = run(cmd + [url]).strip().splitlines()
    path = Path(outp[-1]) if outp else None
    if not path or not path.exists():  # already downloaded earlier -> yt-dlp prints nothing
        cands = sorted(dl.glob("*.mp4"), key=lambda f: f.stat().st_mtime)
        path = cands[-1] if cands else die("download failed")
    print(f"downloaded {path.name} in {time.time() - t0:.0f}s" if set(dl.glob('*.mp4')) != before else f"cached {path.name}")
    return path


def ts(s):
    s = max(0.0, s); h, r = divmod(s, 3600); m, sec = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{sec:05.2f}" if h else f"{int(m)}:{sec:05.2f}"


def parse_t(v):
    if re.fullmatch(r"[\d.]+", str(v)):
        return float(v)
    parts = [float(x) for x in str(v).split(":")]
    return sum(x * 60 ** i for i, x in enumerate(reversed(parts)))


def font_file(family="DejaVu Sans:bold"):
    if shutil.which("fc-match"):
        f = subprocess.run(["fc-match", "-f", "%{file}", family], capture_output=True, text=True).stdout.strip()
        if f and Path(f).exists():
            return f
    for f in ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "C:/Windows/Fonts/arialbd.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if Path(f).exists():
            return f
    return None


def ffesc(p):  # escape a path for use inside an ffmpeg filter argument
    return str(p).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def probe_info(src):
    """duration, video size/fps/codec, audio channel counts - parsed from `ffmpeg -i`, so no ffprobe needed."""
    need("ffmpeg")
    err = subprocess.run([FF, "-hide_banner", "-nostdin", "-i", str(src)], capture_output=True, text=True,
                         errors="replace").stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0.0
    vid, auds = None, []
    for line in err.splitlines():
        if "Stream #" in line and "Video:" in line and vid is None and "attached pic" not in line:
            size = re.search(r", (\d{2,5})x(\d{2,5})", line); fps = re.search(r"([\d.]+) fps", line)
            codec = re.search(r"Video: (\w+)", line)
            if size:
                vid = dict(width=int(size.group(1)), height=int(size.group(2)),
                           fps=float(fps.group(1)) if fps else 0.0, codec=codec.group(1) if codec else "?")
        elif "Stream #" in line and "Audio:" in line:
            auds.append(6 if "5.1" in line else 8 if "7.1" in line else 1 if "mono" in line else 2)
    return dict(dur=dur, video=vid, audio=auds)


# ---------- analyze ----------
def cmd_analyze(a):
    need("ffmpeg")
    if re.match(r"https?://", a.src):
        a.src = str(fetch(a.src, a.frm, a.to))
    src = Path(a.src).expanduser().resolve()
    if not src.exists():
        die(f"no such file {src}")
    w = workdir(src, a.out)
    P = preset(a.preset)["analysis"]
    done = w / "probe.tsv"
    if done.exists() and done.stat().st_mtime > src.stat().st_mtime and not a.force:
        print(done.read_text().strip()); print(f"cached {w}  (use --force to redo)"); return
    info = probe_info(src)
    v, auds, dur = info["video"], info["audio"], info["dur"]
    if not v:
        die("no video stream")
    fps = v["fps"]
    t0 = time.time()
    # audio loudness per 0.5 s
    ai = min(a.audio, max(len(auds) - 1, 0))
    if auds:
        run([FF, *FFQ, "-i", str(src), "-map", f"0:a:{ai}", "-vn", "-af",
             "aresample=8000,asetnsamples=n=4000,astats=metadata=1:reset=1,"
             "ametadata=mode=print:key=lavfi.astats.Overall.RMS_level:file=loud.txt", "-f", "null", "-"], cwd=w)
    # scene cuts + letterbox height, on a tiny low-fps copy
    vf = (f"scale=160:-2,fps={P['analysis_fps']},"
          "cropdetect=limit=24:round=2:reset=1,metadata=mode=print:key=lavfi.cropdetect.h:file=crop.txt,"
          f"select='gt(scene\\,{P['scene_threshold']})',metadata=mode=print:key=lavfi.scene_score:file=scenes.txt")
    run([FF, *FFQ, "-i", str(src), "-map", "0:v:0", "-an", "-vf", vf, "-f", "null", "-"], cwd=w)
    row = (f"name\t{w.name}\nsrc\t{src}\ndur\t{dur:.2f}\nvideo\t{v['width']}x{v['height']} {fps:.2f}fps {v['codec']}\n"
           f"audio_tracks\t{len(auds)} (analysed #{ai}: {auds[ai] if auds else 0}ch)\n"
           f"scaled_h\t{round(160 * v['height'] / v['width'] / 2) * 2}\n")
    done.write_text(row)
    print(row.strip()); print(f"ok {w}  analysed in {time.time() - t0:.0f}s")


def load_series(w):
    loud, cuts, lbox = {}, [], {}
    cur = None
    if (w / "loud.txt").exists():
        for line in (w / "loud.txt").read_text().splitlines():
            if line.startswith("frame:"):
                cur = float(line.split("pts_time:")[1])
            elif "RMS_level=" in line and cur is not None:
                val = line.split("=")[1]
                db = -90.0 if val in ("-inf", "inf", "nan") else max(-90.0, float(val))
                sec = int(cur); loud[sec] = max(loud.get(sec, -90.0), db)
    cur = None
    for line in (w / "scenes.txt").read_text().splitlines() if (w / "scenes.txt").exists() else []:
        if line.startswith("frame:"):
            cuts.append(float(line.split("pts_time:")[1]))
    sh = 0
    for line in (w / "probe.tsv").read_text().splitlines():
        if line.startswith("scaled_h"):
            sh = int(line.split("\t")[1])
    for line in (w / "crop.txt").read_text().splitlines() if (w / "crop.txt").exists() else []:
        if line.startswith("frame:"):
            cur = float(line.split("pts_time:")[1])
        elif "cropdetect.h=" in line and cur is not None:
            sec = int(cur); lbox.setdefault(sec, []).append(int(line.split("=")[1]))
    return loud, cuts, lbox, sh


def zscores(vals):
    if not vals:
        return []
    med = statistics.median(vals)
    mad = statistics.median([abs(x - med) for x in vals]) or 1.0
    return [max(-4.0, min(6.0, (x - med) / (1.4826 * mad))) for x in vals]  # clamp: flat audio makes MAD tiny


def load_words(path):
    out = []
    if path and Path(path).exists():
        for line in Path(path).read_text().splitlines()[1:]:
            p = line.split("\t")
            if len(p) >= 3:
                out.append((float(p[0]), float(p[1]), p[2]))
    return out


# ---------- moments ----------
def cmd_moments(a):
    a.top = min(a.top, 3)  # free edition: top 3
    w = W(a.work)
    cfg = preset(a.preset); M = cfg["moments"]; ratio = cfg["analysis"]["letterbox_ratio"]
    loud, cuts, lbox, sh = load_series(w)
    dur = float(next(l.split("\t")[1] for l in (w / "probe.tsv").read_text().splitlines() if l.startswith("dur")))
    n = int(dur) + 1
    L = [loud.get(i, -90.0) for i in range(n)]
    lz = zscores(L)
    cd = [0] * n
    for c in cuts:
        for i in range(max(0, int(c) - 2), min(n, int(c) + 3)):
            cd[i] += 1
    cz = zscores(cd) if any(cd) else [0] * n
    wb = [0.0] * n
    hype = [h.lower() for h in cfg["hype_words"]]
    words = load_words(a.words)
    text_by_sec = {}
    for s, e, t in words:
        text_by_sec.setdefault(int(s), []).append(t.lower())
    for sec, toks in text_by_sec.items():
        joined = " ".join(toks)
        hits = sum(1 for h in hype if h in joined)
        for i in range(max(0, sec - 1), min(n, sec + 2)):
            wb[i] += hits
    lb = [1.0 if sh and lbox.get(i) and statistics.median(lbox[i]) < sh * ratio else 0.0 for i in range(n)]
    raw = [M["w_loud"] * lz[i] + M["w_cuts"] * cz[i] + M["w_words"] * wb[i] for i in range(n)]
    sm = [sum(raw[max(0, i - 1):i + 2]) / len(raw[max(0, i - 1):i + 2]) for i in range(n)]
    order = sorted(range(n), key=lambda i: -sm[i])
    picks = []
    for i in order:
        if len(picks) >= a.top or sm[i] <= 1.0:
            break
        if all(abs(i - p) >= M["min_gap_s"] for p in picks):
            picks.append(i)
    rows = []
    for p in picks:
        st = max(0.0, p - M["preroll_s"]); en = min(dur, p + M["postroll_s"])
        near = [c for c in cuts if st - 2 <= c <= st + 2]
        if near:
            st = min(near, key=lambda c: abs(c - st))
        if en - st < M["min_len_s"]:
            en = min(dur, st + M["min_len_s"])
        en = min(en, st + M["max_len_s"])
        seg = range(int(st), max(int(st) + 1, int(en)))
        lbf = sum(lb[i] for i in seg if i < n) / len(seg)
        score = sm[p] - (M["letterbox_penalty"] if lbf > 0.4 else 0)
        why = []
        if lz[p] > 1.5: why.append("loud")
        if cz[p] > 1: why.append("fast-cuts")
        if wb[p]: why.append("hype-words")
        if lbf > 0.4: why.append("CUTSCENE?")
        rows.append((score, st, p, en, lz[p], cd[p], lbf, ",".join(why) or "-"))
    rows.sort(key=lambda r: -r[0])
    out = ["id\tstart\tpeak\tend\tdur\tscore\tloud_z\tcuts\tlbox\twhy"]
    for k, (score, st, p, en, z, c, lbf, why) in enumerate(rows, 1):
        out.append(f"m{k:02d}\t{st:.1f}\t{p}\t{en:.1f}\t{en - st:.0f}\t{score:.2f}\t{z:.1f}\t{c}\t{lbf:.0%}\t{why}")
    (w / "moments.tsv").write_text("\n".join(out) + "\n")
    print("\n".join(out))
    print(f"(free: top 3. Pro: unlimited, sentence-snapped, chat spikes, transcript re-rank -> {PRO_URL})")




# ---------- reel ----------
def cmd_reel(a):
    need("ffmpeg")
    cfg = preset(a.preset); R = cfg["reel"]
    src = SRC(a.src); st = parse_t(a.start); en = parse_t(a.end)
    out = OUT(a.out, a.src); out.parent.mkdir(parents=True, exist_ok=True)
    W, H = 1080, 1920
    if a.layout == "fill":
        chain = f"[0:v]crop=ih*9/16:ih,scale={W}:{H},setsar=1[v0]"
    elif a.layout == "blur":
        chain = (f"[0:v]split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=20:2[bg];"
                 f"[b]scale={W}:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[v0]")
    elif a.layout == "facecam":
        die(f"facecam layout: {PRO}")
        if not a.cam:
            die("--cam x,y,w,h (fractions 0-1 of the source frame) required for facecam layout")
        x, y, cw, chh = [float(v) for v in a.cam.split(",")]
        top = int(H * R["facecam_height"]) // 2 * 2; bot = H - top
        chain = (f"[0:v]split[a][b];[a]crop=iw*{cw}:ih*{chh}:iw*{x}:ih*{y},scale={W}:{top}:force_original_aspect_ratio=increase,crop={W}:{top}[cam];"
                 f"[b]crop=ih*{W}/{bot}:ih,scale={W}:{bot}[game];[cam][game]vstack,setsar=1[v0]")
    else:
        die("layout must be fill|blur|facecam")
    last = "v0"
    if getattr(a, "subs", None):
        subs = Path(a.subs).resolve()
        chain += f";[{last}]subtitles=filename='{ffesc(subs)}'[v1]"; last = "v1"
    if a.hook:
        lines = []
        for wd in a.hook.upper().split():  # wrap ~14 chars/line, auto-fit size to 1080 px
            if lines and len(lines[-1]) + 1 + len(wd) <= 14: lines[-1] += " " + wd
            else: lines.append(wd)
        fs = min(110, int(980 / (0.62 * max(len(l) for l in lines))))
        hf = out.with_suffix(".hook.ass")  # ASS via libass: works on bundled ffmpeg builds without drawtext
        hf.write_text(
            "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
            "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
            "MarginR, MarginV, Encoding\n"
            f"Style: Hook,Arial,{fs},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,7,3,8,40,40,220,1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            f"Dialogue: 0,0:00:00.00,{ass_time(R['hook_s'])},Hook,,0,0,0,,{NL.join(lines)}\n")
        chain += f";[{last}]subtitles=filename='{ffesc(hf)}'[v2]"; last = "v2"
    amap = []
    if a.audio and "," in a.audio:
        die(f"multi-track audio mixing: {PRO}")
    if a.audio:
        idx = [int(i) for i in a.audio.split(",")]
        if len(idx) > 1:
            chain += ";" + "".join(f"[0:a:{i}]" for i in idx) + f"amix=inputs={len(idx)}:normalize=0,loudnorm=I={R['lufs']}:TP=-1.5[aout]"
        else:
            chain += f";[0:a:{idx[0]}]loudnorm=I={R['lufs']}:TP=-1.5[aout]"
        amap = ["-map", "[aout]"]
    else:
        has_audio = bool(probe_info(src)["audio"])
        if has_audio:
            chain += f";[0:a:0]loudnorm=I={R['lufs']}:TP=-1.5[aout]"; amap = ["-map", "[aout]"]
    cmd = [FF, *FFQ, "-ss", f"{st:.3f}", "-t", f"{en - st:.3f}", "-i", str(src), "-filter_complex", chain,
           "-map", f"[{last}]", *amap, "-r", str(a.fps or R["fps"]), "-c:v", "libx264", "-preset", "veryfast",
           "-crf", str(R["crf"]), "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
           "-movflags", "+faststart", str(out)]
    t0 = time.time(); run(cmd)
    hf = out.with_suffix(".hook.ass")
    if hf.exists(): hf.unlink()
    print(f"ok {out}  {en - st:.1f}s {a.layout} 1080x1920 in {time.time() - t0:.0f}s")








def ass_time(s):
    h, r = divmod(s, 3600); m, sec = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{sec:05.2f}"




# ---------- policy ----------
def cmd_policy(a):
    cfg = preset(a.preset)
    flags = []
    if a.work and a.start is not None:
        w = W(a.work); _, _, lbox, sh = load_series(w)
        st, en = parse_t(a.start), parse_t(a.end)
        secs = range(int(st), max(int(st) + 1, int(en)))
        lb = sum(1 for i in secs if sh and lbox.get(i) and statistics.median(lbox[i]) < sh * cfg["analysis"]["letterbox_ratio"])
        frac = lb / len(secs)
        if frac > 0.4:
            flags.append(("BLOCK" if frac > 0.8 else "WARN",
                          f"{frac:.0%} letterboxed: cinematic/cutscene or film-style footage. Game publishers (e.g. Rockstar) take down standalone cutscenes; film/TV footage is someone else's copyright. Keep it gameplay/your-own-footage-led or add commentary around it."))
    text = " ".join(filter(None, [a.title, a.desc])).lower()
    hits = [s for s in cfg["spoiler_words"] if s in text]
    if hits:
        flags.append(("WARN", f"spoiler/leak words in title/desc: {', '.join(hits)}. Rewrite without plot reveals."))
    if a.no_voice:
        flags.append(("WARN", "no commentary/mic track: platforms' reused/unoriginal rules favour added voice, captions, edit."))
    if a.no_captions:
        flags.append(("INFO", "no captions: add them (originality + retention)."))
    flags.append(("ASK", "licensed music audible (in-game radio, songs, venue/background music)? Mute, replace or talk over it."))
    flags.append(("ASK", "someone else's video/stream/podcast? Only with permission or inside their clipping campaign; follow its rules (credit, watermark, disclosure)."))
    worst = "BLOCK" if any(f[0] == "BLOCK" for f in flags) else "WARN" if any(f[0] == "WARN" for f in flags) else "PASS"
    print(f"RESULT {worst}")
    for lvl, msg in flags:
        print(f"{lvl}\t{msg}")




# ---------- doctor ----------
def cmd_doctor(a):
    win = os.name == "nt"; mac = sys.platform == "darwin"
    fix = {"ffmpeg": "winget install Gyan.FFmpeg" if win else "brew install ffmpeg" if mac else "sudo apt install ffmpeg",
           "yt-dlp": f"{'python' if win else 'python3'} -m pip install -U yt-dlp",
           "faster-whisper": f"{'python' if win else 'python3'} -m pip install -U faster-whisper"}
    ok = True
    def line(name, good, detail, need=True):
        nonlocal ok
        if not good and need: ok = False
        print(f"{'OK  ' if good else ('MISS' if need else 'opt ')}\t{name}\t{detail}")
    line("python", sys.version_info >= (3, 9), f"{sys.version.split()[0]} ({sys.executable})")
    fb = ffbin()
    line("ffmpeg", bool(fb), (fb + ("" if shutil.which("ffmpeg") else "  (bundled)")) if fb else f"fix: {fix['ffmpeg']}  or pip install imageio-ffmpeg")
    try:
        import yt_dlp; ytd = f"module {yt_dlp.version.__version__}"
    except Exception:
        ytd = shutil.which("yt-dlp")
    line("yt-dlp (links)", bool(ytd), ytd or f"fix: {fix['yt-dlp']}", need=False)
    try:
        import faster_whisper; fw = "installed"
    except Exception:
        fw = None
    line("captions / batch / recaps / thumbnails", False, PRO, need=False)
    f = font_file(); line("font (sheet labels)", bool(f), f or "none: contact sheets have no labels", need=False)
    try:
        BASE.mkdir(parents=True, exist_ok=True); (BASE / ".w").write_text("x"); (BASE / ".w").unlink(); line("output dir", True, str(BASE))
    except Exception as e:
        line("output dir", False, f"{BASE}: {e}  (set CLIP_HARNESS_DIR)")
    print(f"presets\t{', '.join(p.stem for p in sorted((ROOT / 'presets').glob('*.json')))}  (default {os.environ.get('CLIP_HARNESS_PRESET', 'general')})")
    print("RESULT READY" if ok else "RESULT FIX THE MISS LINES")




def main():
    ap = argparse.ArgumentParser(prog="ch", description=__doc__)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("analyze", help="probe + loudness + scene cuts + letterbox (cached)")
    p.add_argument("src", help="video file OR link (YouTube/Twitch/Kick...)"); p.add_argument("--out"); p.add_argument("--audio", type=int, default=0)
    p.add_argument("--from", dest="frm", help="link only: download from this time"); p.add_argument("--to", help="link only: download until")
    p.add_argument("--preset", default=os.environ.get("CLIP_HARNESS_PRESET", "general")); p.add_argument("--force", action="store_true"); p.set_defaults(f=cmd_analyze)
    p = sp.add_parser("moments", help="rank highlight windows -> moments.tsv")
    p.add_argument("work"); p.add_argument("--top", type=int, default=12); p.add_argument("--words")
    p.add_argument("--preset", default=os.environ.get("CLIP_HARNESS_PRESET", "general")); p.set_defaults(f=cmd_moments)

    p = sp.add_parser("reel", help="render a 9:16 reel")
    p.add_argument("src"); p.add_argument("start"); p.add_argument("end"); p.add_argument("out")
    p.add_argument("--layout", default="blur", help="blur | fill"); p.add_argument("--cam"); p.add_argument("--hook")
    p.add_argument("--audio", help="track index(es) to mix, e.g. 0,1"); p.add_argument("--fps", type=int)
    p.add_argument("--preset", default=os.environ.get("CLIP_HARNESS_PRESET", "general")); p.set_defaults(f=cmd_reel)




    p = sp.add_parser("policy", help="pre-post risk check")
    p.add_argument("--work"); p.add_argument("--start"); p.add_argument("--end"); p.add_argument("--title"); p.add_argument("--desc")
    p.add_argument("--no-voice", action="store_true"); p.add_argument("--no-captions", action="store_true")
    p.add_argument("--preset", default=os.environ.get("CLIP_HARNESS_PRESET", "general")); p.set_defaults(f=cmd_policy)

    p = sp.add_parser("doctor", help="check setup: python, ffmpeg, yt-dlp, whisper, fonts"); p.set_defaults(f=cmd_doctor)

    a = ap.parse_args(); a.f(a)


if __name__ == "__main__":
    main()
