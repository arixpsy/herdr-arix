#!/usr/bin/env python3
"""Search YouTube, pick a result with fzf, play it with mpv. Runs on macOS, Linux and Windows.

The video mode starts as sidebar and "v" at the prompt cycles it:
  sidebar  frames in the yt-video mod above this terminal
  window   a small floating mpv window
  tct      text art in this terminal
  null     audio only
A URL typed at the prompt plays directly.

Run it with python -B: a __pycache__ folder written here would reload the mod.
"""
import os, re, shutil, subprocess, sys, tempfile, threading, time

sys.dont_write_bytecode = True
from mpvctl import IPC

HERE = os.path.dirname(os.path.abspath(__file__))
FRAME = os.path.join(HERE, "..", "yt-video", "frame.jpg")
FRAMES = os.path.join(os.path.expanduser("~"), ".cache", "ytplayer", "frames")
LOG = os.path.join(tempfile.gettempdir(), "ytplayer.log")
MODES = ["sidebar", "window", "tct", "null"]
HEIGHT = {"sidebar": 720, "window": 1080}

# YouTube answers 403 on the direct streams of some videos and drops the HLS
# streams of others, so try direct first and fall back to HLS.
FORMATS = [
    "bv*[height<={h}]+ba/b",
    "bv*[height<={h}][protocol^=m3u8]+ba[protocol^=m3u8]/b[protocol^=m3u8]",
]

if sys.platform == "darwin":
    os.environ["PATH"] = "/opt/homebrew/bin" + os.pathsep + os.environ.get("PATH", "")


def clear():
    print("\033[2J\033[H", end="", flush=True)


def sync_frames(proc):
    """Keep the yt-video mod's frame.jpg on mpv's newest finished frame.

    One file name on purpose: Herdr keeps every image it has shown under a new
    name or new content forever (about 1.2 MB per frame), but replaces a
    rewritten file in place. The cost is Herdr's file watcher, about 8 fps.
    """
    while proc.poll() is None:
        names = sorted(n for n in os.listdir(FRAMES) if n.endswith(".jpg"))
        if len(names) > 1:
            # mpv may still be writing the newest file, so show the one before it.
            try:
                os.replace(os.path.join(FRAMES, names[-2]), FRAME)
            except PermissionError:
                pass  # Windows refuses while Herdr has frame.jpg open; the next pass catches up.
            for n in names[:-2]:
                try:
                    os.unlink(os.path.join(FRAMES, n))
                except OSError:
                    pass
        time.sleep(0.03)
    for n in os.listdir(FRAMES):
        os.unlink(os.path.join(FRAMES, n))
    if os.path.exists(FRAME):
        os.unlink(FRAME)


def mpv(mode, fmt, url):
    args = ["mpv", "--log-file=" + LOG, "--input-ipc-server=" + IPC,
            # mpv buffers up to 200 MB of each stream by default. 32 MB ahead is minutes of video.
            "--demuxer-max-bytes=32MiB", "--demuxer-max-back-bytes=8MiB",
            "--ytdl-format=" + fmt]
    if mode == "sidebar":
        os.makedirs(FRAMES, exist_ok=True)
        for n in os.listdir(FRAMES):
            os.unlink(os.path.join(FRAMES, n))
        args += ["--vo=image", "--vo-image-format=jpg", "--vo-image-jpeg-quality=85",
                 "--vo-image-outdir=" + FRAMES, "--vf=fps=12,scale=540:-2", "--really-quiet"]
    elif mode == "window":
        args += ["--ontop", "--no-border", "--geometry=480x270-24-24", "--autofit=480x270",
                 "--force-window=immediate", "--really-quiet"]
    elif mode == "null":
        args += ["--no-video", "--term-osd-bar"]
    else:
        args += ["--vo=" + mode, "--really-quiet"]
    proc = subprocess.Popen(args + [url])
    if mode == "sidebar":
        threading.Thread(target=sync_frames, args=(proc,), daemon=True).start()
    try:
        return proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        return proc.wait()


def play(mode, url):
    clear()
    print("Playing " + url + "\nStop it with the stop button.")
    for fmt in FORMATS:
        # mpv exits 2 when the video failed to load.
        if mpv(mode, fmt.format(h=HEIGHT.get(mode, 480)), url) != 2:
            return
    clear()
    print("Playback failed:\n")
    with open(LOG, encoding="utf-8", errors="replace") as f:
        errors = [re.sub(r"^\[[^]]*\]\[.\]\[[^]]*\] ", "", l)[:200]
                  for l in f if re.search(r"\]\[(e|f)\]\[", l)]
    print("".join(errors[-6:]))
    input("Press Enter to go back to search. ")


def search(q):
    print("searching...")
    found = subprocess.run(
        ["yt-dlp", "--flat-playlist", "--print",
         "%(id)s\t%(title)s  [%(duration_string)s] %(channel)s", "ytsearch20:" + q],
        capture_output=True, text=True, encoding="utf-8").stdout
    pick = subprocess.run(
        ["fzf", "--with-nth=2..", "--delimiter=\t", "--prompt=" + q + " > ",
         "--height=100%", "--reverse"],
        input=found, stdout=subprocess.PIPE, text=True, encoding="utf-8").stdout
    return pick.split("\t")[0].strip()


def main():
    missing = [p for p in ("mpv", "yt-dlp", "fzf") if not shutil.which(p)]
    mode = "sidebar"
    while True:
        clear()
        if missing:
            print("Install first: " + ", ".join(missing) + "\n")
        try:
            q = input(f"YouTube [vo={mode}]  search or URL (v=cycle video mode): ").strip()
        except KeyboardInterrupt:
            continue
        except EOFError:
            return
        if q == "v":
            mode = MODES[(MODES.index(mode) + 1) % len(MODES)]
        elif q.startswith("http"):
            play(mode, q)
        elif q:
            vid = search(q)
            if vid:
                play(mode, "https://www.youtube.com/watch?v=" + vid)


main()
