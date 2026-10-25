"""
Caption window.
A Toplevel window — second window under the same Tk root as the control panel.
Move it to your second screen and press F for full-screen.
"""

import queue
import tkinter as tk
from tkinter import font as tkfont

MAX_LINES    = 6
SCROLL_DELAY = 50
BG_COLOR     = "#0a0a0a"
TEXT_COLOR   = "#f0f0e8"
EVENT_COLOR  = "#555550"
LABEL_COLOR  = "#888880"


class CaptionWindow:
    def __init__(self, root, font_size=36):
        self.font_size = font_size
        self._queue    = queue.Queue()
        self._is_fullscreen = False
        self._last_label    = None  # tracks speaker of the previous entry

        # Toplevel shares the same Tk root — safe on macOS
        self._win = tk.Toplevel(root)
        self._win.title("CaptionKit — Captions")
        self._win.configure(bg=BG_COLOR)
        self._win.geometry("1200x400")
        self._win.bind("<f>",      self._toggle_fullscreen)
        self._win.bind("<F>",      self._toggle_fullscreen)
        self._win.bind("<Escape>", self._exit_fullscreen)

        self._build_ui()
        self._win.after(SCROLL_DELAY, self._drain_queue)

    def push(self, entry):
        """Thread-safe: queue a transcript entry for display."""
        self._queue.put(entry)

    def _build_ui(self):
        frame = tk.Frame(self._win, bg=BG_COLOR)
        frame.pack(fill=tk.BOTH, expand=True, padx=48, pady=32)

        caption_font = tkfont.Font(family="Georgia", size=self.font_size)
        label_font   = tkfont.Font(family="Georgia", size=int(self.font_size * 0.55))
        event_font   = tkfont.Font(family="Georgia", size=int(self.font_size * 0.45),
                                   slant="italic")

        self._text = tk.Text(
            frame, bg=BG_COLOR, fg=TEXT_COLOR, font=caption_font,
            wrap=tk.WORD, state=tk.DISABLED, relief=tk.FLAT, bd=0,
            cursor="none", spacing1=8, spacing3=16,
        )
        self._text.pack(fill=tk.BOTH, expand=True)
        self._text.tag_configure("label",      font=label_font,   foreground=LABEL_COLOR)
        self._text.tag_configure("transcript", font=caption_font, foreground=TEXT_COLOR)
        self._text.tag_configure("event",      font=event_font,   foreground=EVENT_COLOR)

        tk.Label(self._win, text="F  full screen   ·   Esc  exit",
                 bg=BG_COLOR, fg="#2a2a28", font=("Georgia", 11)).pack(pady=(0, 8))

    def _toggle_fullscreen(self, event=None):
        self._is_fullscreen = not self._is_fullscreen
        self._win.attributes("-fullscreen", self._is_fullscreen)

    def _exit_fullscreen(self, event=None):
        self._is_fullscreen = False
        self._win.attributes("-fullscreen", False)

    def _drain_queue(self):
        try:
            while True:
                self._render(self._queue.get_nowait())
        except queue.Empty:
            pass
        self._win.after(SCROLL_DELAY, self._drain_queue)

    def _render(self, entry):
        w = self._text
        w.configure(state=tk.NORMAL)
        if entry["type"] == "event":
            w.insert(tk.END, f"\n{entry['text']}\n", "event")
            self._last_label = None  # next transcript starts a new block
        else:
            label = entry.get("label", "")
            text  = entry.get("text", "")
            if label == self._last_label:
                # Same speaker as previous entry — continue the paragraph
                w.insert(tk.END, f" {text}", "transcript")
            else:
                w.insert(tk.END, f"\n{label}\n", "label")
                w.insert(tk.END, text, "transcript")
            self._last_label = label
        line_count = int(w.index(tk.END).split(".")[0])
        if line_count > MAX_LINES * 5:
            w.delete("1.0", f"{line_count - MAX_LINES * 4}.0")
        w.configure(state=tk.DISABLED)
        w.see(tk.END)
