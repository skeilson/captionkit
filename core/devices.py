"""
Audio device discovery and monitoring.
Detects connected microphones, identifies ReSpeakers by name,
and polls for hot-plug events (new mics added mid-session).
"""

import threading
import time

import sounddevice as sd

KNOWN_ARRAY_KEYWORDS = [
    "respeaker", "seeed", "array", "usb audio", "usb mic", "xvf",
]

HOT_PLUG_POLL_INTERVAL = 3.0  # seconds between device list checks


def get_input_devices():
    """Return a list of available audio input devices."""
    devices = []
    try:
        for idx, dev in enumerate(sd.query_devices()):
            if dev["max_input_channels"] > 0:
                name_lower = dev["name"].lower()
                is_array = any(kw in name_lower for kw in KNOWN_ARRAY_KEYWORDS)
                devices.append({
                    "id": idx,
                    "name": dev["name"],
                    "channels": dev["max_input_channels"],
                    "sample_rate": int(dev["default_samplerate"]),
                    "is_array": is_array,
                })
    except Exception as e:
        print(f"[devices] Error querying devices: {e}")
    return devices


class DeviceMonitor:
    """
    Polls for USB audio device changes in a background thread.
    Calls on_added(device) or on_removed(device) when devices change.
    """

    def __init__(self, on_added=None, on_removed=None):
        self.on_added = on_added
        self.on_removed = on_removed
        self._known = {d["id"]: d for d in get_input_devices()}
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def current_devices(self):
        return list(self._known.values())

    def _poll(self):
        while self._running:
            time.sleep(HOT_PLUG_POLL_INTERVAL)
            try:
                current = {d["id"]: d for d in get_input_devices()}
                for dev_id, dev in current.items():
                    if dev_id not in self._known:
                        self._known[dev_id] = dev
                        if self.on_added:
                            self.on_added(dev)
                for dev_id in list(self._known):
                    if dev_id not in current:
                        dev = self._known.pop(dev_id)
                        if self.on_removed:
                            self.on_removed(dev)
            except Exception as e:
                print(f"[DeviceMonitor] Poll error: {e}")
