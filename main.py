#!/usr/bin/env python3
"""
CaptionKit — real-time captioning for in-person meetings.

Usage:  python3 main.py
"""

import os
import signal
import sys
import tkinter as tk

from core.config import load_config
from core.session import Session
from ui.caption_window import CaptionWindow
from ui.control_window import ControlWindow

# Resolve config.yaml next to this file, so it's found no matter which
# folder the command is run from.
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(PROJECT_DIR, "config.yaml")


def main():
    config = load_config(CONFIG_PATH)

    # Single Tk root — both windows live under this
    root = tk.Tk()

    session = Session(config)

    show_caption = config.get("show_caption_window", True)
    caption_win = None
    if show_caption:
        caption_win = CaptionWindow(root, font_size=config.get("font_size", 36))

    session.start()

    control_win = ControlWindow(root, session, caption_win)
    session.on_transcript = control_win.push

    def shutdown(sig, frame):
        print("\n[CaptionKit] Shutting down...")
        session.stop()
        root.destroy()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    root.mainloop()
    session.stop()


if __name__ == "__main__":
    main()
