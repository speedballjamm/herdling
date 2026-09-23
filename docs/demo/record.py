"""Records the demo: three clips of real play (driven by the test harness, recorded with
asciinema), composited into a styled window with captions.

    python3 docs/demo/record.py [--font-dir DIR]

Needs tmux, asciinema 3, agg, ffmpeg (brew install tmux asciinema agg ffmpeg), Pillow
(pip install pillow) and the JetBrains Mono font (installed, or in --font-dir).
Writes docs/demo.gif (README), docs/demo.mp4 (social posts) and docs/social-preview.png.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DOCS = os.path.join(ROOT, "docs")
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, ROOT)
from harness import Game  # noqa: E402

COLS, ROWS = 132, 36
FONT_PX = 28                      # agg renders at 2x; everything is scaled down later
CANVAS = (1920, 1080)
FPS = 30

# Catppuccin Mocha: background, foreground, then the 16 ANSI colours
THEME = ("1e1e2e,cdd6f4,"
         "45475a,f38ba8,a6e3a1,f9e2af,89b4fa,f5c2e7,94e2d5,bac2de,"
         "585b70,f38ba8,a6e3a1,f9e2af,89b4fa,f5c2e7,94e2d5,a6adc8")
BG = (0x1e, 0x1e, 0x2e)


# ------------------------------------------------------------------ recording

class Clip:
    """One game, recorded from its first frame; `mark_in`/`mark_out` pick the part we keep."""

    def __init__(self, name, args, caption, seed=None, speed=1.0):
        self.name, self.caption, self.speed = name, caption, speed
        self.home = tempfile.mkdtemp(prefix=f"hl-{name}-", dir="/tmp")
        fake_home = os.path.join(self.home, "home")
        os.makedirs(fake_home)
        # a throwaway $HOME with a plain prompt, so no real user or hostname shows up
        with open(os.path.join(fake_home, ".bash_profile"), "w") as f:
            f.write('PS1="\\W \\$ "\n')
        if seed:
            with open(os.path.join(self.home, "progress.json"), "w") as f:
                json.dump(seed, f)
        self.g = Game(f"demo-{name}", args=args, cols=COLS, rows=ROWS, home=self.home,
                      env={"HOME": fake_home, "SHELL": "/bin/bash", "BASH_SILENCE_DEPRECATION_WARNING": "1"})
        self.cast = os.path.join(self.home, "clip.cast")
        self.rec = subprocess.Popen(
            ["asciinema", "rec", "--headless", "--window-size", f"{COLS}x{ROWS}", "--overwrite",
             "-c", f"tmux -L {self.g.outer} attach", self.cast],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # the recording's clock starts at its first frame, a moment after asciinema launches
        end = time.time() + 10
        while time.time() < end and not self._has_output():
            time.sleep(0.02)
        self.t0 = time.time()
        self.t_in = self.t_out = None

    def _has_output(self):
        try:
            with open(self.cast) as f:
                return sum(1 for _ in f) > 1
        except OSError:
            return False

    def mark_in(self):
        self.t_in = time.time() - self.t0

    def mark_out(self):
        self.t_out = time.time() - self.t0

    def finish(self):
        self.g.close()
        self.rec.wait(timeout=20)


def seeded(worlds_done):
    """Progress with the first N worlds cleared, so the HUD shows a mid-game rank."""
    from game.worlds import WORLDS
    data = {"xp": 0, "missions": {}, "streak": 4, "best_streak": 6, "keys": {}, "dojo_best": 9,
            "settings": {"bell": False}}
    for w in WORLDS:
        if w.num < worlds_done:
            for m in w.missions:
                data["missions"][m.id] = {"stars": 3, "xp": m.xp, "best": m.par / 2, "skipped": False}
                data["xp"] += m.xp
    return data


def clip_tmux():
    c = Clip("tmux", ("play", "1.2"), "Coming from tmux? It catches your habits.", seed=seeded(1))
    g = c.g
    g.wait_title("1.2")
    time.sleep(0.8)
    c.mark_in()
    time.sleep(1.2)
    g.prefix("%", delay=0.1)
    g.wait_hud("tmux")
    time.sleep(2.8)
    g.prefix("-", delay=0.1)
    g.wait_done("1.2")
    time.sleep(1.4)
    c.mark_out()
    c.finish()
    return c


def clip_herd():
    c = Clip("herd", ("play", "5.5"), "Boss fight: four AI agents, three projects. Keep the herd moving.",
             seed=seeded(5), speed=1.6)
    g = c.g
    g.wait_title("5.5")
    time.sleep(0.8)
    c.mark_in()
    answered = set()
    end = time.time() + 90
    while len(answered) < 4 and time.time() < end:
        blocked = [n for n, a in g.agents().items() if a["agent_status"] == "blocked" and n not in answered]
        if blocked:
            time.sleep(1.2)                 # let the notice land on screen first
            g.prefix("o", delay=0.9)
            focused = g.snap()["focused_pane_id"]
            who = [n for n, a in g.agents().items() if a["pane_id"] == focused]
            name = who[0] if who and who[0] in blocked else blocked[0]
            if name != (who[0] if who else None):
                g.call("pane.focus", pane_id=g.agents()[name]["pane_id"])
                time.sleep(0.4)
            g.type("y", delay=1.0)
            answered.add(name)
        time.sleep(0.2)
    g.wait_done("5.5", timeout=40)
    time.sleep(1.4)
    c.mark_out()
    c.finish()
    return c


def clip_dojo():
    c = Clip("dojo", ("dojo",), "Dojo: 60-second speed drills. Chain combos, beat your best.", seed=seeded(5))
    g = c.g
    g.close_card()
    g.wait_title("DOJO")
    time.sleep(0.3)
    c.mark_in()
    end = time.time() + 8
    while time.time() < end:
        prompt = g.runtime().get("prompt", "")
        if "Move one pane" in prompt:
            g.prefix({"LEFT": "h", "RIGHT": "l", "UP": "k", "DOWN": "j"}[prompt.split()[-1].rstrip("!")])
        elif "RIGHT" in prompt:
            g.prefix("v")
        elif "BELOW" in prompt:
            g.prefix("-")
        elif "Unzoom" in prompt or prompt == "Zoom!":
            g.prefix("z")
        elif "New tab" in prompt:
            g.prefix("c")
            g.keys("Enter")
        elif "Next tab" in prompt:
            g.prefix("n")
        elif "Close this pane" in prompt:
            g.prefix("x")
        else:
            time.sleep(0.2)
            continue
        try:
            g.wait(lambda: g.runtime().get("prompt") != prompt, 6, "next drill")
        except AssertionError:
            pass
        time.sleep(0.35)
    time.sleep(1.0)
    c.mark_out()
    c.finish()
    return c


# ------------------------------------------------------------------ compositing

def run(*argv):
    subprocess.run(argv, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def cast_events(path):
    """[(seconds, output)] from an asciicast (v2 absolute times or v3 intervals)."""
    with open(path) as f:
        lines = f.read().splitlines()
    v3 = json.loads(lines[0]).get("version") == 3
    t, out = 0.0, []
    for line in lines[1:]:
        e = json.loads(line)
        t = t + e[0] if v3 else e[0]
        if e[1] == "o":
            out.append((t, e[2]))
    return out


def safe_out(clip):
    """Cut before the game leaves Herdr: its shutdown, or a full-screen lesson card."""
    for t, data in cast_events(clip.cast):
        if t > clip.t_in + 1 and ("server exited" in data or "Enter to continue" in data):
            return min(clip.t_out, t - 0.25)
    return clip.t_out


def render(clip, font_dir, work):
    """cast -> gif (agg) -> trimmed mp4 of just the terminal."""
    gif = os.path.join(work, f"{clip.name}.gif")
    agg = ["agg", "--font-size", str(FONT_PX), "--font-family", "JetBrains Mono,Apple Color Emoji",
           "--theme", THEME, "--line-height", "1.3", "--idle-time-limit", "60", "--fps-cap", str(FPS)]
    if font_dir:
        agg += ["--font-dir", font_dir]
    run(*agg, clip.cast, gif)
    out = os.path.join(work, f"{clip.name}.term.mp4")
    run("ffmpeg", "-y", "-ss", f"{clip.t_in:.2f}", "-to", f"{safe_out(clip):.2f}", "-i", gif,
        "-vf", f"setpts=PTS/{clip.speed},fps={FPS},crop=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p", "-c:v", "libx264", "-crf", "12", out)
    return out


def layout(term_w, term_h):
    """Where the window and the terminal inside it go on the canvas."""
    W, H = CANVAS
    cap_h, bar_h, pad = 150, 52, 22
    max_w, max_h = W - 240, H - cap_h - bar_h - 2 * pad - 50
    s = min(max_w / term_w, max_h / term_h)
    tw, th = int(term_w * s) // 2 * 2, int(term_h * s) // 2 * 2
    win_w, win_h = tw + 2 * pad, th + bar_h + 2 * pad
    wx, wy = (W - win_w) // 2, cap_h
    return dict(tw=tw, th=th, tx=wx + pad, ty=wy + bar_h + pad, wx=wx, wy=wy, ww=win_w, wh=win_h, bar=bar_h)


def font(size, bold=False):
    from PIL import ImageFont
    for path in ("/System/Library/Fonts/SFNS.ttf", "/System/Library/Fonts/Helvetica.ttc"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def frame_png(L, caption, path, title="herdling"):
    """The canvas: gradient background, window with shadow and title bar, caption. The terminal
    area is transparent; the video goes underneath."""
    from PIL import Image, ImageDraw, ImageFilter
    W, H = CANVAS
    bg = Image.new("RGB", (W, H))
    top, bottom = (58, 36, 92), (18, 52, 86)          # plum to deep blue
    px = bg.load()
    for y in range(H):
        for x in range(W):
            t = (0.7 * y / H + 0.3 * x / W)
            px[x, y] = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    img = bg.convert("RGBA")
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (L["wx"], L["wy"] + 18, L["wx"] + L["ww"], L["wy"] + L["wh"] + 18), 18, fill=(0, 0, 0, 150))
    img = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(28)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((L["wx"], L["wy"], L["wx"] + L["ww"], L["wy"] + L["wh"]), 16, fill=BG + (255,),
                        outline=(255, 255, 255, 40), width=1)
    d.rounded_rectangle((L["wx"], L["wy"], L["wx"] + L["ww"], L["wy"] + L["bar"]), 16, fill=(24, 24, 37, 255))
    d.rectangle((L["wx"], L["wy"] + L["bar"] - 16, L["wx"] + L["ww"], L["wy"] + L["bar"]), fill=(24, 24, 37, 255))
    for i, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        cx, cy = L["wx"] + 30 + i * 28, L["wy"] + L["bar"] // 2
        d.ellipse((cx - 8, cy - 8, cx + 8, cy + 8), fill=col + (255,))
    f = font(22)
    d.text((L["wx"] + L["ww"] / 2, L["wy"] + L["bar"] / 2), title, font=f, fill=(166, 173, 200, 255), anchor="mm")
    if caption:
        d.text((W / 2, L["wy"] / 2 + 4), caption, font=font(46), fill=(255, 255, 255, 255), anchor="mm")
    # punch the terminal hole
    hole = Image.new("L", (W, H), 255)
    ImageDraw.Draw(hole).rectangle((L["tx"], L["ty"], L["tx"] + L["tw"] - 1, L["ty"] + L["th"] - 1), fill=0)
    img.putalpha(hole)
    img.save(path)


def compose(clip, term_mp4, work):
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height", "-of", "csv=p=0", term_mp4],
                           capture_output=True, text=True, check=True).stdout.strip().split(",")
    L = layout(int(probe[0]), int(probe[1]))
    png = os.path.join(work, f"{clip.name}.frame.png")
    frame_png(L, clip.caption, png)
    out = os.path.join(work, f"{clip.name}.mp4")
    W, H = CANVAS
    run("ffmpeg", "-y", "-i", term_mp4, "-i", png, "-filter_complex",
        f"[0]scale={L['tw']}:{L['th']}:flags=lanczos,pad={W}:{H}:{L['tx']}:{L['ty']}:color=black[v];"
        f"[v][1]overlay=0:0,fps={FPS},format=yuv420p",
        "-c:v", "libx264", "-crf", "16", "-preset", "slow", out)
    return out, L


def duration(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                 "csv=p=0", path], capture_output=True, text=True, check=True).stdout)


def join(parts, out, fade=0.5):
    args, filt, prev, offset = [], [], "[0]", 0.0
    for p in parts:
        args += ["-i", p]
    for i in range(1, len(parts)):
        offset += duration(parts[i - 1]) - fade
        filt.append(f"{prev}[{i}]xfade=transition=fade:duration={fade}:offset={offset:.2f}[x{i}]")
        prev = f"[x{i}]"
    run("ffmpeg", "-y", *args, "-filter_complex", ";".join(filt), "-map", prev,
        "-c:v", "libx264", "-crf", "18", "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out)


def to_gif(mp4, gif, width=1000, fps=12):
    pal = gif + ".palette.png"
    base = f"fps={fps},scale={width}:-1:flags=lanczos"
    run("ffmpeg", "-y", "-i", mp4, "-vf", f"{base},palettegen=max_colors=128:stats_mode=diff", pal)
    run("ffmpeg", "-y", "-i", mp4, "-i", pal, "-lavfi", f"{base}[x];[x][1:v]paletteuse=dither=sierra2_4a:diff_mode=rectangle", gif)
    os.remove(pal)


def social_preview(term_mp4, at, L, work, out):
    """1280x640: title over one frame of the herd."""
    from PIL import Image, ImageDraw
    still = os.path.join(work, "still.png")
    run("ffmpeg", "-y", "-ss", f"{at:.2f}", "-i", term_mp4, "-frames:v", "1", still)
    png = os.path.join(work, "preview.frame.png")
    frame_png(L, "", png)
    base = Image.new("RGBA", CANVAS, (0, 0, 0, 255))
    base.paste(Image.open(still).resize((L["tw"], L["th"]), Image.LANCZOS), (L["tx"], L["ty"]))
    img = Image.alpha_composite(base, Image.open(png)).convert("RGB")
    # drop the caption band, keep the window, and put the title on top
    W, H = CANVAS
    img = img.crop((0, L["wy"] - 150, W, H)).resize((1280, round(1280 * (H - L["wy"] + 150) / W)), Image.LANCZOS)
    card = Image.new("RGB", (1280, 640))
    card.paste(img, (0, 640 - img.height + 150))
    band = Image.open(png).convert("RGB").crop((0, 0, W, 10)).resize((1280, 170))
    card.paste(band, (0, 0))
    d = ImageDraw.Draw(card)
    d.text((640, 62), "herdling", font=font(72), fill=(255, 255, 255), anchor="mm")
    d.text((640, 128), "learn Herdr by playing it", font=font(34), fill=(205, 214, 244), anchor="mm")
    card.save(out, optimize=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font-dir")
    ap.add_argument("--keep", action="store_true", help="keep the work directory")
    a = ap.parse_args()
    for tool in ("tmux", "asciinema", "agg", "ffmpeg", "ffprobe", "herdr"):
        if not shutil.which(tool):
            sys.exit(f"needs {tool}")
    work = tempfile.mkdtemp(prefix="hl-demo-")
    clips = []
    for rec in (clip_tmux, clip_herd, clip_dojo):
        print(f"recording {rec.__name__[5:]}…", flush=True)
        clips.append(rec())
    parts = []
    for c in clips:
        print(f"rendering {c.name}…", flush=True)
        term = render(c, a.font_dir, work)
        part, L = compose(c, term, work)
        parts.append(part)
        if c.name == "herd":
            social_preview(term, duration(term) * 0.55, L, work, os.path.join(DOCS, "social-preview.png"))
    print("joining…", flush=True)
    mp4 = os.path.join(DOCS, "demo.mp4")
    join(parts, mp4)
    to_gif(mp4, os.path.join(DOCS, "demo.gif"))
    for c in clips:
        shutil.rmtree(c.home, ignore_errors=True)
    if not a.keep:
        shutil.rmtree(work, ignore_errors=True)
    else:
        print("work files:", work)
    print("wrote docs/demo.mp4, docs/demo.gif, docs/social-preview.png")


if __name__ == "__main__":
    main()
