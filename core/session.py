"""
Session manager.
Owns all active MicStreams, the device monitor, the transcript log,
and handles saving the output file.
"""

import os
import threading
import time
from datetime import datetime

from core.devices import DeviceMonitor, get_input_devices
from core.transcription import MicStream


class Session:
    def __init__(self, config, on_transcript=None, on_device_added=None, on_device_removed=None):
        self.config               = config
        self.on_transcript        = on_transcript
        self.on_device_added_cb   = on_device_added
        self.on_device_removed_cb = on_device_removed

        self.chunk_seconds  = config.get("chunk_seconds", 1.5)
        self.output_path    = os.path.expanduser(
            config.get("output_path", "~/Desktop/captionkit_transcript.txt"))
        self.friendly_names = config.get("mic_names", {}) or {}

        self._streams       = {}
        self._lock          = threading.Lock()
        self._monitor       = None
        self._session_start = datetime.now()

        out_dir = os.path.dirname(self.output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(self.output_path, "w") as f:
            started = self._session_start.strftime("%B %d, %Y %I:%M %p")
            f.write(f"CaptionKit transcript — {started}\n")
            f.write("=" * 60 + "\n\n")

    def start(self):
        for dev in get_input_devices():
            self._add_stream(dev)
        self._monitor = DeviceMonitor(
            on_added=self._handle_device_added,
            on_removed=self._handle_device_removed,
        )
        self._monitor.start()
        engine = self.config.get("engine", "whisper")
        print(f"[Session] Started using '{engine}' engine. Transcript → {self.output_path}")

    def stop(self):
        if self._monitor:
            self._monitor.stop()
        with self._lock:
            for stream in self._streams.values():
                stream.stop()
        print("[Session] Stopped.")

    def set_enabled(self, device_id, enabled):
        with self._lock:
            if device_id in self._streams:
                self._streams[device_id].set_enabled(enabled)

    def set_gain(self, device_id, gain):
        with self._lock:
            if device_id in self._streams:
                self._streams[device_id].set_gain(gain)

    def active_devices(self):
        with self._lock:
            return [{"id": s.device_id, "label": s.label, "enabled": s.enabled,
                     "gain": s.gain, "device": s.device}
                    for s in self._streams.values()]

    def _label_for(self, device):
        name = device["name"]
        for keyword, friendly in self.friendly_names.items():
            if keyword.lower() in name.lower():
                return friendly
        return name.split("(")[0].strip()

    def _add_stream(self, device):
        label  = self._label_for(device)
        stream = MicStream(
            device=device,
            label=label,
            on_transcript=self._handle_transcript,
            config=self.config,
            chunk_seconds=self.chunk_seconds,
        )
        with self._lock:
            self._streams[device["id"]] = stream
        stream.start()
        print(f"[Session] Stream started: {label} (device {device['id']})")

    def _handle_device_added(self, device):
        timestamp = time.strftime("%I:%M %p")
        label     = self._label_for(device)
        self._add_stream(device)
        entry = {"type": "event", "text": f"Microphone connected: {label}",
                 "timestamp": timestamp, "device_id": device["id"], "label": label}
        self._emit(entry)
        if self.on_device_added_cb:
            self.on_device_added_cb(device)

    def _handle_device_removed(self, device):
        timestamp = time.strftime("%I:%M %p")
        with self._lock:
            stream = self._streams.pop(device["id"], None)
        if stream:
            stream.stop()
            entry = {"type": "event", "text": f"Microphone disconnected: {stream.label}",
                     "timestamp": timestamp, "device_id": device["id"], "label": stream.label}
            self._emit(entry)
        if self.on_device_removed_cb:
            self.on_device_removed_cb(device)

    def _handle_transcript(self, device_id, label, text, timestamp):
        entry = {"type": "transcript", "text": text, "timestamp": timestamp,
                 "device_id": device_id, "label": label}
        self._emit(entry)

    def _emit(self, entry):
        self._save_entry(entry)
        if self.on_transcript:
            self.on_transcript(entry)

    def _save_entry(self, entry):
        try:
            with open(self.output_path, "a") as f:
                if entry["type"] == "transcript":
                    f.write(f"[{entry['timestamp']}] {entry['label']}: {entry['text']}\n")
                else:
                    f.write(f"\n--- {entry['text']} ({entry['timestamp']}) ---\n\n")
        except Exception as e:
            print(f"[Session] File write error: {e}")
