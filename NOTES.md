# CaptionKit — Notes & Future Improvements

## Current status

Working end-to-end with the MacBook's built-in microphone:
- Audio capture, device detection, hot-plug support: working
- Whisper (`faster-whisper`) and Moonshine engines both wired up, switchable via `config.yaml`
- Control window (mic cards, gain, on/off) and Caption window (second-screen display): working
- Transcript saved to file in real time
- Custom vocabulary corrections (find/replace) and Whisper initial_prompt: working
- Consecutive same-speaker chunks now merge into one paragraph on screen

Current recommended config as a baseline:
```yaml
engine: whisper
model_size: base
chunk_seconds: 3.0
beam_size: 1
```
(`SILENCE_THRESHOLD` lowered from 0.01 to 0.003 in core/transcription.py)

## Known limitation: chunk-boundary accuracy

Audio is split into fixed, non-overlapping chunks (`chunk_seconds`). Whisper
transcribes each chunk in isolation, so words that fall right at a chunk
boundary get cut off mid-word/mid-sentence with no surrounding context —
this produces garbled text at the start/end of chunks.

This is a real contributor to the accuracy issues seen so far, separate
from model size, beam size, or silence threshold.

## PINNED — Future improvement: overlapping chunks

**When:** revisit once the ReSpeaker arrives and is in use.

**What:** instead of hard-cutting audio into back-to-back chunks, each new
chunk includes ~1 second of audio from the tail of the previous chunk.
Whisper then has context on both sides of any boundary. The overlapping
text from consecutive chunks needs to be de-duplicated before display/save
(e.g. by matching the trailing words of chunk N against the leading words
of chunk N+1).

**Why it's pinned rather than done now:** it's a real architectural change
worth doing carefully, and testing it against the MacBook's built-in mic
may not be representative — the ReSpeaker's cleaner signal could change
how much this matters in practice. Better to test the new mic + current
chunking first, then layer this on if accuracy is still lacking.

## Other things to evaluate once the ReSpeaker arrives

- Whether `model_size: small` becomes viable again now that chunking/
  silence threshold are fixed — `small` was the original starting point
  and may perform better with a cleaner input signal.
- Re-test Moonshine vs Whisper side by side with the ReSpeaker — Moonshine's
  accuracy issues earlier may have been partly a mic-quality problem.
- Multi-mic hot-plug testing (only tested with a single device so far).
- Test `whisper.cpp` with Apple Metal GPU acceleration as a drop-in replacement
  for `faster-whisper` — could enable faster inference and larger model sizes
  on Apple Silicon, closing the gap with cloud-based approaches.

## PINNED — Future project: wireless microphone array

**Decision:** sticking with USB/wired ReSpeaker hardware for now. Wireless
is a future phase once the wired pipeline is solid and battle-tested at
an actual event.

### Hardware to buy when ready

Per additional table node (beyond the one running wired from the laptop):
- Raspberry Pi Zero 2W (~$15)
- 16GB MicroSD card (~$8)
- Micro-USB to USB-A adapter (~$3)
- Small USB power bank, 10,000mAh (~$20)
- ReSpeaker USB Mic Array XVF3000 (~$50)

**Per table total: ~$96**

Also buy once regardless of table count:
- GL.iNet travel router or similar (~$30) — creates a private Wi-Fi
  network independent of venue infrastructure. Makes everything reliable
  and removes dependence on venue IT.

### Physical setup per table
```
[ReSpeaker, center of table]
        |
    short USB cable
        |
[Pi Zero 2W, taped under table]
        |
    USB power bank
```
No cables running across the room floor.

### One-time Pi setup (per device)
1. Flash Raspberry Pi OS Lite (headless) via Raspberry Pi Imager
2. Pre-configure Wi-Fi and SSH in the imager before flashing
3. SSH in, install Python + sounddevice + portaudio
4. Copy the audio sender script (to be written, ~50-100 lines)
5. Configure sender to auto-start on boot via systemd

Once set up, each Pi's role at an event is: plug in power → connects
to Wi-Fi → starts streaming → done. No manual intervention.

### Event setup flow (once built)
1. Arrive at venue, plug in travel router
2. Place one Pi + ReSpeaker + power bank per table, power on
3. Pis boot and connect to router automatically (~30 seconds)
4. Start CaptionKit on laptop — mic cards appear for each table
5. Move caption window to second screen, press F for full-screen

### `config.yaml` addition (to be implemented)
```yaml
network_mics:
  - ip: 192.168.1.101
    label: Front Table
  - ip: 192.168.1.102
    label: Back Left
  - ip: 192.168.1.103
    label: Back Right
```

### Code changes required
- `core/devices.py` — add `NetworkDeviceMonitor` that reads from
  `network_mics` in config and retries connections for Pis not yet online
- `core/transcription.py` — add `NetworkMicStream` that reads audio
  from a UDP/TCP socket instead of sounddevice, feeds the same audio
  queue and transcription loop — everything downstream is unchanged
- New `pi/sender.py` — runs on each Pi, captures from the ReSpeaker
  via sounddevice, streams audio over the network to the laptop
- UI unchanged — network nodes get mic cards identical to USB devices

**When to tackle:** after wired multi-mic is tested at a real event and
the overlapping-chunks accuracy improvement is in place.
