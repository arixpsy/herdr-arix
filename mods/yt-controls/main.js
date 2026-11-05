// Play/pause, stop, a draggable seek bar and volume for the sidebar YouTube player.
// Talks to its mpv through mpvctl.py, which uses mpv's IPC socket (a named pipe on Windows).

import { View, div } from "gpui-kit";
import { v_flex, h_flex } from "gpui-base";
import { exec, appHome, theme, shared, setShared, window } from "herdr";

const CTL = () => `${appHome()}/mods/yt-controls/mpvctl.py`;
// Windows installs Python as python; its python3 is a Microsoft Store stub.
const PYTHON = () => (window().platform === "windows" ? "python" : "python3");

function clock(sec) {
  if (sec == null || !isFinite(sec)) return "--:--";
  const s = Math.floor(sec), h = Math.floor(s / 3600), m = Math.floor(s / 60) % 60;
  const ss = String(s % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${ss}` : `${m}:${ss}`;
}

function fraction(e) {
  if (!e.bounds || !e.local_position) return null;
  return Math.min(1, Math.max(0, e.local_position.x / e.bounds.width));
}

export default class YtControls extends View {
  init(_props, cx) {
    this.state = {};
    // The bar being held ("seek" or "volume") and where, 0..1.
    this.drag = null;
    cx.timer.every(500, (cx) => this.call(cx, ["state"]));
  }

  call(cx, args) {
    cx.spawn(async (cx) => {
      try {
        const r = await exec(PYTHON(), ["-B", CTL(), ...args]);
        this.state = JSON.parse(r.stdout || "{}");
      } catch {
        this.state = {};
      }
      // yt-video reads this to choose between the picture and its hint.
      const playing = this.state.duration != null;
      if (shared("yt.playing") !== playing) setShared("yt.playing", playing);
      cx.notify();
    });
  }

  commit(cx) {
    const d = this.drag;
    this.drag = null;
    if (d?.bar === "seek" && this.state.duration) {
      this.state.time = d.at * this.state.duration;
      this.call(cx, ["seek", String(this.state.time)]);
    } else if (d?.bar === "volume") {
      this.state.volume = Math.round(d.at * 100);
      this.call(cx, ["volume", String(this.state.volume)]);
    }
    cx.notify();
  }

  bar(t, name, value, enabled) {
    const at = this.drag?.bar === name ? this.drag.at : value;
    return div().id(`yt-${name}`).h(16).flex().items_center()
      .when(enabled, (el) => el.cursor_pointer()
        .on_mouse_down("left", (e, cx) => { this.drag = { bar: name, at: fraction(e) ?? at }; cx.notify(); })
        .on_mouse_move((e, cx) => {
          if (this.drag?.bar !== name) return;
          this.drag.at = fraction(e) ?? this.drag.at;
          cx.notify();
        })
        .on_mouse_up("left", (_e, cx) => this.commit(cx)))
      .child(div().relative().w_full().h(4).rounded(2).bg(t.border)
        .child(div().absolute().left(0).top(0).h(4).rounded(2).bg(enabled ? t.accent : t.dim).w(`${at * 100}%`)
          .child(div().absolute().top(-4).right(-6).size(12).rounded(6).bg(enabled ? t.accent : t.dim))));
  }

  button(t, id, label, enabled, args) {
    return div().id(id).flex_none().w(28).h(22).rounded(5)
      .flex().items_center().justify_center().text_size(12)
      .bg(t.raised).text_color(enabled ? t.foreground : t.dim)
      .when(enabled, (el) => el.cursor_pointer().hover((s) => s.bg(t.hover))
        .on_click((_e, cx) => this.call(cx, args)))
      .child(label);
  }

  render(cx) {
    const t = theme();
    const { title, pause, time, duration, volume, mute } = this.state;
    const live = duration != null;
    const connected = volume != null;
    const seekAt = live && duration ? (time ?? 0) / duration : 0;
    const shown = this.drag?.bar === "seek" && duration ? this.drag.at * duration : time;
    const vol = this.drag?.bar === "volume" ? Math.round(this.drag.at * 100) : Math.round(volume ?? 0);

    return v_flex().id("yt-controls").size_full().px(12).py(6).gap(5).bg(t.chrome)
      .on_mouse_down_out((_e, cx) => { if (this.drag) { this.drag = null; cx.notify(); } })
      .child(div().truncate().text_size(11.5).text_color(live ? t.muted : t.dim)
        .child(live ? (title ?? "") : "Nothing playing"))
      .child(h_flex().gap(8).items_center()
        .child(this.button(t, "yt-toggle", pause === false ? "❚❚" : "▶", live, ["toggle"]))
        .child(this.button(t, "yt-stop", "■", live, ["stop"]))
        .child(this.bar(t, "seek", seekAt, live).flex_1())
        .child(div().flex_none().text_size(11).text_color(t.dim)
          .child(`${clock(shown)} / ${clock(duration)}`)))
      .child(h_flex().gap(8).items_center()
        .child(this.button(t, "yt-mute", mute ? "🔇" : "🔊", connected, ["mute"]))
        .child(this.bar(t, "volume", vol / 100, connected).flex_1())
        .child(div().flex_none().w(28).text_size(11).text_color(t.dim).child(connected ? `${vol}%` : "")));
  }
}
