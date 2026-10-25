"""
Transcription engine.
Each MicStream captures audio from one device and feeds it to a transcription
"engine" — either Whisper (faster-whisper) or Moonshine (useful-moonshine-onnx).
Both engines are wrapped behind a common transcribe(audio) -> [text, ...] interface
so MicStream doesn't need to know which one is active.

Engine selection happens in config.yaml via the `engine` field.
"""

import queue
import threading
import time

import numpy as np
import sounddevice as sd

SAMPLE_RATE       = 16000
SILENCE_THRESHOLD = 0.003  # raise toward 0.005-0.01 if background noise causes hallucinations

_engine      = None
_engine_lock = threading.Lock()


# ----------------------------------------------------------------------
# Engine wrappers — both expose transcribe(audio: np.ndarray) -> list[str]
# ----------------------------------------------------------------------

class WhisperEngine:
    """Wraps faster-whisper. Good multilingual coverage, large ecosystem."""

    def __init__(self, model_size="small", beam_size=1, initial_prompt=None):
        from faster_whisper import WhisperModel
        print(f"[whisper] Loading '{model_size}' model... (first run downloads it)")
        self._model = WhisperModel(model_size, device="cpu", compute_type="int8")
        self.beam_size = beam_size
        self.initial_prompt = initial_prompt
        print("[whisper] Model ready.")

    def transcribe(self, audio):
        segments, _ = self._model.transcribe(
            audio, language="en", vad_filter=True, beam_size=self.beam_size,
            initial_prompt=self.initial_prompt,
        )
        return [seg.text.strip() for seg in segments if seg.text.strip()]


class MoonshineEngine:
    """
    Wraps Moonshine (useful-moonshine-onnx). Purpose-built for real-time,
    resource-constrained transcription. English only. Two sizes: tiny, base.
    """

    def __init__(self, model_size="base"):
        import moonshine_onnx
        self._moonshine = moonshine_onnx
        self.model_name = f"moonshine/{model_size}"
        print(f"[moonshine] Using '{self.model_name}' (first run downloads it)")
        # Warm up — first call triggers model download/load
        _ = self._moonshine.transcribe(np.zeros(SAMPLE_RATE, dtype=np.float32), self.model_name)
        print("[moonshine] Model ready.")

    def transcribe(self, audio):
        result = self._moonshine.transcribe(audio, self.model_name)
        return [text.strip() for text in result if text.strip()]


def get_engine(config):
    """
    Load the configured transcription engine once and reuse it across all
    mic streams. Reads `engine` and the relevant size field from config.
    """
    global _engine
    with _engine_lock:
        if _engine is None:
            engine_name = config.get("engine", "whisper").lower()
            if engine_name == "moonshine":
                _engine = MoonshineEngine(model_size=config.get("moonshine_model", "base"))
            else:
                _engine = WhisperEngine(
                    model_size=config.get("model_size", "small"),
                    beam_size=config.get("beam_size", 1),
                    initial_prompt=config.get("initial_prompt"),
                )
    return _engine


def rms(audio):
    return np.sqrt(np.mean(audio ** 2))


def apply_corrections(text, corrections):
    """
    Apply a dictionary of find/replace corrections to transcribed text.
    Matching is case-insensitive on the 'find' side; replacement preserves
    the case given in config. Useful for consistently-mis-heard names,
    jargon, or acronyms (e.g. "moon shining" -> "Moonshine").
    """
    import re
    for find, replace in corrections.items():
        pattern = re.compile(re.escape(find), re.IGNORECASE)
        text = pattern.sub(replace, text)
    return text


class MicStream:
    """
    Captures audio from a single input device and transcribes it in real time
    using whichever engine is configured.
    on_transcript: callback(device_id, label, text, timestamp)
    """

    def __init__(self, device, label, on_transcript, config,
                 gain=1.0, chunk_seconds=1.5):
        self.device        = device
        self.device_id     = device["id"]
        self.label         = label
        self.on_transcript = on_transcript
        self.config        = config
        self.gain          = gain
        self.chunk_seconds = chunk_seconds
        self.corrections   = config.get("corrections", {}) or {}
        self.enabled       = True
        self._audio_queue  = queue.Queue()
        self._running      = False

    def start(self):
        self._running = True
        get_engine(self.config)  # ensure engine is loaded before threads start
        threading.Thread(target=self._capture_loop, daemon=True,
                         name=f"capture-{self.device_id}").start()
        threading.Thread(target=self._transcribe_loop, daemon=True,
                         name=f"transcribe-{self.device_id}").start()

    def stop(self):
        self._running = False

    def set_gain(self, gain):
        self.gain = max(0.0, min(2.0, gain))

    def set_enabled(self, enabled):
        self.enabled = enabled

    def _capture_loop(self):
        chunk_samples = int(SAMPLE_RATE * self.chunk_seconds)
        buffer        = np.zeros(chunk_samples, dtype=np.float32)
        write_pos     = 0

        def callback(indata, frames, time_info, status):
            nonlocal write_pos
            if not self.enabled:
                return
            audio = np.clip(indata[:, 0].copy() * self.gain, -1.0, 1.0)
            space = chunk_samples - write_pos
            if frames <= space:
                buffer[write_pos:write_pos + frames] = audio
                write_pos += frames
            else:
                buffer[write_pos:] = audio[:space]
                self._audio_queue.put(buffer.copy())
                write_pos = frames - space
                buffer[:write_pos] = audio[space:]

        try:
            with sd.InputStream(device=self.device_id, samplerate=SAMPLE_RATE,
                                channels=1, dtype="float32", callback=callback):
                while self._running:
                    time.sleep(0.1)
        except Exception as e:
            print(f"[MicStream:{self.label}] Capture error: {e}")

    def _transcribe_loop(self):
        engine = get_engine(self.config)
        debug  = self.config.get("debug", False)
        while self._running:
            try:
                audio = self._audio_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            level = rms(audio)
            if debug:
                print(f"[{self.label}] audio level: {level:.4f}")
            if not self.enabled or level < SILENCE_THRESHOLD:
                continue
            try:
                result = engine.transcribe(audio)
                if debug:
                    print(f"[{self.label}] raw result: {result!r}")
                for text in result:
                    if self.corrections:
                        text = apply_corrections(text, self.corrections)
                    timestamp = time.strftime("%I:%M %p")
                    self.on_transcript(self.device_id, self.label, text, timestamp)
            except Exception as e:
                if debug:
                    import traceback
                    traceback.print_exc()
                else:
                    print(f"[MicStream:{self.label}] Transcription error: {e}")
