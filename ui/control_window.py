"""
Control window.
The main Tk root window — operator-facing panel with mic cards and live feed.
"""

import queue
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

BG      = "#1a1a18"
CARD    = "#242420"
BORDER  = "#333330"
TEXT    = "#e8e8e0"
DIM     = "#666660"
ACCENT  = "#c8b878"
ON_COL  = "#4a7a4a"
OFF_COL = "#5a3a3a"
SCROLL  = 80


class MicCard(tk.Frame):
    def __init__(self, parent, device_info, on_toggle, on_gain_change, **kw):
        super().__init__(parent, bg=CARD, **kw)
        self.device_id      = device_info["id"]
        self.label          = device_info["label"]
        self.on_toggle      = on_toggle
        self.on_gain_change = on_gain_change
        self._enabled       = True
        self._build()

    def _build(self):
        self.configure(padx=16, pady=14)
        lf = tkfont.Font(family="Menlo", size=13, weight="bold")
        sf = tkfont.Font(family="Menlo", size=10)

        hdr = tk.Frame(self, bg=CARD)
        hdr.pack(fill=tk.X)
        self._name = tk.Label(hdr, text=self.label, bg=CARD, fg=TEXT, font=lf, anchor="w")
        self._name.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._btn = tk.Button(hdr, text="ON", bg=ON_COL, fg=TEXT, font=sf,
                              relief=tk.FLAT, padx=10, pady=2, cursor="hand2",
                              command=self._toggle)
        self._btn.pack(side=tk.RIGHT)

        row = tk.Frame(self, bg=CARD)
        row.pack(fill=tk.X, pady=(10, 0))
        tk.Label(row, text="GAIN", bg=CARD, fg=DIM, font=sf, width=5, anchor="w").pack(side=tk.LEFT)
        self._gain_var = tk.DoubleVar(value=1.0)
        ttk.Scale(row, from_=0.0, to=2.0, orient=tk.HORIZONTAL,
                  variable=self._gain_var, command=self._on_gain).pack(
                      side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        self._gain_lbl = tk.Label(row, text="1.0×", bg=CARD, fg=ACCENT, font=sf, width=4)
        self._gain_lbl.pack(side=tk.RIGHT)

    def _toggle(self):
        self._enabled = not self._enabled
        self._btn.configure(text="ON" if self._enabled else "OFF",
                            bg=ON_COL if self._enabled else OFF_COL)
        self.on_toggle(self.device_id, self._enabled)

    def _on_gain(self, value):
        g = round(float(value), 1)
        self._gain_lbl.configure(text=f"{g}×")
        self.on_gain_change(self.device_id, g)

    def mark_disconnected(self):
        self._name.configure(fg=DIM, text=f"{self.label}  [disconnected]")
        self._btn.configure(state=tk.DISABLED)


class ControlWindow:
    def __init__(self, root, session, caption_window):
        self._root          = root
        self.session        = session
        self.caption_window = caption_window
        self._queue         = queue.Queue()
        self._cards         = {}
        self._last_label    = None  # tracks speaker of previous feed entry

        self._root.title("CaptionKit — Control")
        self._root.configure(bg=BG)
        self._root.geometry("480x640")

        self._build_ui()
        self._populate_cards()
        self._root.after(SCROLL, self._drain_queue)

    def push(self, entry):
        self._queue.put(entry)

    def _build_ui(self):
        tf = tkfont.Font(family="Menlo", size=15, weight="bold")
        sf = tkfont.Font(family="Menlo", size=9)
        mf = tkfont.Font(family="Menlo", size=11)

        bar = tk.Frame(self._root, bg=BG, pady=16)
        bar.pack(fill=tk.X, padx=20)
        tk.Label(bar, text="CAPTIONKIT", bg=BG, fg=ACCENT, font=tf).pack(side=tk.LEFT)
        subtitle_font = tkfont.Font(family="Menlo", size=10)
        tk.Label(bar, text="operator panel", bg=BG, fg=DIM, font=subtitle_font).pack(
            side=tk.LEFT, padx=(10, 0), pady=(4, 0))

        tk.Frame(self._root, bg=BORDER, height=1).pack(fill=tk.X, padx=20)

        tk.Label(self._root, text="MICROPHONES", bg=BG, fg=DIM, font=sf, anchor="w"
                 ).pack(fill=tk.X, padx=20, pady=(16, 6))

        self._cards_frame = tk.Frame(self._root, bg=BG)
        self._cards_frame.pack(fill=tk.X, padx=20)

        tk.Frame(self._root, bg=BORDER, height=1).pack(fill=tk.X, padx=20, pady=(16, 0))
        tk.Label(self._root, text="LIVE FEED", bg=BG, fg=DIM, font=sf, anchor="w"
                 ).pack(fill=tk.X, padx=20, pady=(12, 6))

        self._feed = tk.Text(self._root, bg=CARD, fg=TEXT, font=mf, wrap=tk.WORD,
                             state=tk.DISABLED, relief=tk.FLAT, bd=0,
                             height=10, spacing1=3, spacing3=5)
        self._feed.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        self._feed.tag_configure("label", foreground=ACCENT)
        self._feed.tag_configure("event", foreground=DIM,
                                 font=tkfont.Font(family="Menlo", size=10, slant="italic"))

    def _populate_cards(self):
        for dev in self.session.active_devices():
            self._add_card(dev)

    def _add_card(self, device_info):
        if device_info["id"] in self._cards:
            return
        card = MicCard(self._cards_frame, device_info,
                       on_toggle=self.session.set_enabled,
                       on_gain_change=self.session.set_gain)
        card.pack(fill=tk.X, pady=(0, 2))
        tk.Frame(self._cards_frame, bg=BORDER, height=1).pack(fill=tk.X, pady=(0, 8))
        self._cards[device_info["id"]] = card

    def _remove_card(self, device_id):
        if device_id in self._cards:
            self._cards[device_id].mark_disconnected()

    def _drain_queue(self):
        try:
            while True:
                entry = self._queue.get_nowait()
                self._render_feed(entry)
                if self.caption_window:
                    self.caption_window.push(entry)
                if entry["type"] == "event":
                    dev_id = entry.get("device_id")
                    if "connected" in entry["text"] and "dis" not in entry["text"]:
                        for dev in self.session.active_devices():
                            if dev["id"] == dev_id:
                                self._root.after(0, lambda d=dev: self._add_card(d))
                    elif "disconnected" in entry["text"] and dev_id:
                        self._root.after(0, lambda d=dev_id: self._remove_card(d))
        except queue.Empty:
            pass
        self._root.after(SCROLL, self._drain_queue)

    def _render_feed(self, entry):
        self._feed.configure(state=tk.NORMAL)
        if entry["type"] == "event":
            self._feed.insert(tk.END, f"  {entry['text']}\n", "event")
            self._last_label = None
        else:
            label = entry.get("label", "")
            text  = entry.get("text", "")
            if label == self._last_label:
                self._feed.insert(tk.END, f" {text}")
            else:
                self._feed.insert(tk.END, f"\n[{entry.get('timestamp', '')}] ", "label")
                self._feed.insert(tk.END, f"{label}: {text}")
            self._last_label = label
        lines = int(self._feed.index(tk.END).split(".")[0])
        if lines > 100:
            self._feed.delete("1.0", f"{lines - 80}.0")
        self._feed.configure(state=tk.DISABLED)
        self._feed.see(tk.END)
