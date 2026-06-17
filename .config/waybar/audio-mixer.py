#!/usr/bin/env python3
"""Waybar audio mixer — anchored below bar via gtk-layer-shell, closes on outside click or Escape."""

import subprocess
import re
import sys
import os
import signal

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, Gdk, GLib, GtkLayerShell

CSS = """
* {
    font-family: "JetBrainsMono Nerd Font", "Noto Sans", monospace;
    font-size: 13px;
}
window#mixer {
    background-color: rgba(30, 30, 46, 0.97);
    border: 1px solid rgba(137, 180, 250, 0.35);
    border-radius: 0 0 8px 8px;
}
#main-box {
    padding: 10px 14px 12px;
    min-width: 280px;
}
.section-header {
    color: #6c7086;
    font-size: 10px;
    margin-bottom: 4px;
    margin-top: 2px;
}
.row-name {
    color: #89b4fa;
    font-size: 12px;
}
.app-name {
    color: #cdd6f4;
    font-size: 12px;
}
.empty-label {
    color: #6c7086;
    font-size: 12px;
    padding: 4px 0;
}
slider {
    background-color: #45475a;
    border-radius: 4px;
    min-height: 4px;
}
slider:hover { background-color: #585b70; }
trough {
    background-color: #313244;
    border-radius: 4px;
    min-height: 4px;
}
highlight {
    background-color: #89b4fa;
    border-radius: 4px;
    min-height: 4px;
}
.app-row highlight { background-color: #cba6f7; }
scale { margin: 0 4px; }
.mute-btn {
    background: rgba(137, 180, 250, 0.10);
    color: #cdd6f4;
    border: 1px solid rgba(137, 180, 250, 0.22);
    border-radius: 5px;
    padding: 1px 7px;
    min-width: 28px;
    font-size: 13px;
}
.mute-btn:hover { background: rgba(137, 180, 250, 0.22); }
.mute-btn.muted {
    background: rgba(243, 139, 168, 0.15);
    border-color: rgba(243, 139, 168, 0.4);
    color: #f38ba8;
}
.vol-label {
    color: #a6adc8;
    font-size: 11px;
    min-width: 36px;
}
separator {
    background-color: rgba(137, 180, 250, 0.12);
    margin: 5px 0;
}
"""


def run(cmd):
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return ""


def _parse_blocks(output, header_re):
    items, current = [], None
    for line in output.splitlines():
        m = re.match(header_re, line)
        if m:
            if current is not None:
                items.append(current)
            current = {"_id": int(m.group(1))}
            continue
        if current is None:
            continue
        m2 = re.match(r'^\s+Name:\s+(.+)', line)
        if m2:
            current["name"] = m2.group(1).strip()
        m2 = re.match(r'^\s+Description:\s+(.+)', line)
        if m2:
            current["description"] = m2.group(1).strip()
        m2 = re.match(r'^\s+Mute:\s+(\w+)', line)
        if m2:
            current["muted"] = m2.group(1).strip() == "yes"
        m2 = re.match(r'^\s+Volume:.*?(\d+)%', line)
        if m2 and "volume" not in current:
            current["volume"] = int(m2.group(1))
        m2 = re.match(r'^\s+application\.name\s*=\s*"(.+)"', line)
        if m2:
            current["app_name"] = m2.group(1)
        m2 = re.match(r'^\s+application\.process\.binary\s*=\s*"(.+)"', line)
        if m2:
            current["app_binary"] = m2.group(1)
    if current is not None:
        items.append(current)
    return items


def get_default_sink():
    name = run(["pactl", "get-default-sink"]).strip()
    sinks = _parse_blocks(run(["pactl", "list", "sinks"]), r'^Sink #(\d+)')
    for s in sinks:
        if s.get("name") == name:
            return s
    return sinks[0] if sinks else None


def get_sink_inputs():
    items = _parse_blocks(run(["pactl", "list", "sink-inputs"]), r'^Sink Input #(\d+)')
    return [i for i in items if i.get("app_name") or i.get("app_binary")]


def _mute_icon(muted):
    name = "audio-volume-muted-symbolic" if muted else "audio-volume-high-symbolic"
    return Gtk.Image.new_from_icon_name(name, Gtk.IconSize.BUTTON)


def make_control_row(muted, volume, on_vol, on_mute, app_row=False):
    ctrl = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    if app_row:
        ctrl.get_style_context().add_class("app-row")

    btn = Gtk.Button()
    btn.set_image(_mute_icon(muted))
    btn.get_style_context().add_class("mute-btn")
    if muted:
        btn.get_style_context().add_class("muted")

    def _toggle(b):
        on_mute()
        ctx = b.get_style_context()
        if ctx.has_class("muted"):
            ctx.remove_class("muted")
            b.set_image(_mute_icon(False))
        else:
            ctx.add_class("muted")
            b.set_image(_mute_icon(True))

    btn.connect("clicked", lambda b: _toggle(b))
    ctrl.pack_start(btn, False, False, 0)

    adj = Gtk.Adjustment(value=volume, lower=0, upper=100,
                         step_increment=1, page_increment=5)
    scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
    scale.set_draw_value(False)
    scale.connect("value-changed", lambda s: on_vol(int(s.get_value())))
    ctrl.pack_start(scale, True, True, 0)

    lbl = Gtk.Label(label=f"{volume}%", xalign=1)
    lbl.get_style_context().add_class("vol-label")
    scale.connect("value-changed", lambda s, l: l.set_text(f"{int(s.get_value())}%"), lbl)
    ctrl.pack_start(lbl, False, False, 0)

    return ctrl


class AudioMixer(Gtk.Window):

    def __init__(self, quit_fn):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self._quit = quit_fn
        self.set_name("mixer")
        self.set_decorated(False)
        self.set_resizable(False)

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 38)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, 4)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self._build_ui()
        self.connect("key-press-event", self._on_key)
        self.add_events(Gdk.EventMask.LEAVE_NOTIFY_MASK)
        self.connect("leave-notify-event", self._on_leave)

    def _on_key(self, _win, event):
        if event.keyval == Gdk.KEY_Escape:
            self._quit()

    def _on_leave(self, _win, event):
        # NONLINEAR = pointer crossed to an unrelated surface (actual window exit)
        if event.detail == Gdk.NotifyType.NONLINEAR:
            self._quit()

    def _build_ui(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_name("main-box")
        self.add(outer)

        sink = get_default_sink()
        if sink:
            hdr = Gtk.Label(label="MASTER", xalign=0)
            hdr.get_style_context().add_class("section-header")
            outer.pack_start(hdr, False, False, 0)

            desc = (sink.get("description") or sink.get("name", "Output"))
            if len(desc) > 40:
                desc = desc[:38] + "…"
            name_lbl = Gtk.Label(label=desc, xalign=0)
            name_lbl.get_style_context().add_class("row-name")
            outer.pack_start(name_lbl, False, False, 0)

            n = sink["name"]
            outer.pack_start(make_control_row(
                muted=sink.get("muted", False),
                volume=sink.get("volume", 0),
                on_vol=lambda v, n=n: subprocess.Popen(["pactl", "set-sink-volume", n, f"{v}%"]),
                on_mute=lambda n=n: subprocess.Popen(["pactl", "set-sink-mute", n, "toggle"]),
            ), False, False, 0)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        outer.pack_start(sep, False, False, 0)

        hdr = Gtk.Label(label="APPS", xalign=0)
        hdr.get_style_context().add_class("section-header")
        outer.pack_start(hdr, False, False, 0)

        inputs = get_sink_inputs()
        if not inputs:
            lbl = Gtk.Label(label="Nothing playing", xalign=0)
            lbl.get_style_context().add_class("empty-label")
            outer.pack_start(lbl, False, False, 0)
        else:
            for i, inp in enumerate(inputs):
                if i > 0:
                    outer.pack_start(
                        Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL),
                        False, False, 0
                    )
                raw = inp.get("app_name") or inp.get("app_binary") or f"Stream #{inp['_id']}"
                label = raw[:40] + "…" if len(raw) > 40 else raw

                name_lbl = Gtk.Label(label=label, xalign=0)
                name_lbl.get_style_context().add_class("app-name")
                outer.pack_start(name_lbl, False, False, 0)

                iid = inp["_id"]
                outer.pack_start(make_control_row(
                    muted=inp.get("muted", False),
                    volume=inp.get("volume", 100),
                    on_vol=lambda v, i=iid: subprocess.Popen(
                        ["pactl", "set-sink-input-volume", str(i), f"{v}%"]),
                    on_mute=lambda i=iid: subprocess.Popen(
                        ["pactl", "set-sink-input-mute", str(i), "toggle"]),
                    app_row=True,
                ), False, False, 0)


def main():
    pidfile = "/tmp/waybar-audio-mixer.pid"

    if os.path.exists(pidfile):
        try:
            with open(pidfile) as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, signal.SIGTERM)
            os.remove(pidfile)
        except (ProcessLookupError, ValueError, OSError):
            try:
                os.remove(pidfile)
            except OSError:
                pass
        sys.exit(0)

    with open(pidfile, "w") as f:
        f.write(str(os.getpid()))

    def quit_all(*_):
        try:
            os.remove(pidfile)
        except OSError:
            pass
        Gtk.main_quit()

    signal.signal(signal.SIGTERM, quit_all)
    signal.signal(signal.SIGINT, quit_all)

    mixer = AudioMixer(quit_fn=quit_all)
    mixer.show_all()

    try:
        Gtk.main()
    finally:
        try:
            os.remove(pidfile)
        except OSError:
            pass


if __name__ == "__main__":
    main()
