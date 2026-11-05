#!/usr/bin/env python3
"""Talk to the YouTube player's mpv over its IPC socket (a named pipe on Windows).

  mpvctl.py state        print {"title", "pause", "time", "duration", "volume", "mute"} or {}
  mpvctl.py toggle       pause or resume
  mpvctl.py seek <sec>   jump to an absolute position
  mpvctl.py volume <n>   set the volume, 0 to 100
  mpvctl.py mute         mute or unmute
  mpvctl.py stop         quit mpv, back to the search prompt
"""
import json, os, socket, sys

if os.name == "nt":
    IPC = r"\\.\pipe\ytplayer-mpv"
else:
    IPC = os.path.join(os.path.expanduser("~"), ".cache", "ytplayer", "mpv.sock")


def connect():
    if os.name == "nt":
        return open(IPC, "r+b", buffering=0)
    s = socket.socket(socket.AF_UNIX)
    s.settimeout(1)
    s.connect(IPC)
    return s.makefile("rwb", buffering=0)


def ask(*commands):
    with connect() as f:
        for i, c in enumerate(commands):
            f.write((json.dumps({"command": c, "request_id": i}) + "\n").encode())
        replies = {}
        while len(replies) < len(commands):
            line = f.readline()
            if not line:
                raise OSError("mpv closed the socket")
            msg = json.loads(line)
            # mpv also sends events on the same connection; they have no request_id.
            if "request_id" in msg:
                replies[msg["request_id"]] = msg.get("data")
    return [replies[i] for i in range(len(commands))]


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "state"
    try:
        if cmd == "toggle":
            ask(["cycle", "pause"])
        elif cmd == "seek":
            ask(["seek", float(sys.argv[2]), "absolute"])
        elif cmd == "volume":
            ask(["set_property", "volume", max(0.0, min(100.0, float(sys.argv[2])))])
        elif cmd == "mute":
            ask(["cycle", "mute"])
        elif cmd == "stop":
            try:
                ask(["quit"])
            except OSError:
                pass
            print("{}")
            return
        keys = ["media-title", "pause", "time-pos", "duration", "volume", "mute"]
        values = ask(*(["get_property", k] for k in keys))
        names = ["title", "pause", "time", "duration", "volume", "mute"]
        print(json.dumps(dict(zip(names, values))))
    except (OSError, ValueError):
        print("{}")


if __name__ == "__main__":
    main()
