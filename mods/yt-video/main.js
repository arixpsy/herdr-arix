// The sidebar YouTube player's picture. The player's framesync.py keeps
// frame.jpg on mpv's newest frame; Herdr reloads the image when it changes.
// Kitty graphics and per-frame file names are avoided: herdr-app keeps those
// images forever. Each new frame also reloads this mod, so it keeps no state
// of its own: yt-controls shares whether something is playing.

import { View, div, image } from "gpui-kit";
import { theme, shared } from "herdr";

export default class YtVideo extends View {
  render() {
    const t = theme();
    if (!shared("yt.playing")) {
      return div().size_full().bg(t.chrome).flex().items_center().justify_center()
        .text_size(12).text_color(t.dim).child("Search below to play a video");
    }
    return div().size_full().bg("#000000").child(image("mods/yt-video/frame.jpg").size_full());
  }
}
