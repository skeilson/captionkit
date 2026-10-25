# CaptionKit

[![Security checks](https://github.com/skeilson/captionkit/actions/workflows/security.yml/badge.svg)](https://github.com/skeilson/captionkit/actions/workflows/security.yml)
[![CodeQL](https://github.com/skeilson/captionkit/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/skeilson/captionkit/actions/workflows/github-code-scanning/codeql)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Real-time, local captioning for in-person meetings, initially built for deaf and
hard-of-hearing attendees at conferences, offsites, and group meetings.

Allows for multiple inputs (i.e. microphones) to be connected with manual control for each.

Everything runs on your laptop. No internet connection, accounts, or API
keys are needed once the models are downloaded.

> **Status: early development.** CaptionKit works end to end, but caption
> accuracy is still being tuned and it has not yet been used at a live event.
> See [Roadmap](#roadmap).

> **Accessibility note.** CaptionKit is an assistive tool, not a replacement
> for professional real-time captioning (CART) or sign language interpreting.
> Automatic captions make mistakes, especially with names, jargon, accents,
> and overlapping speakers. Where captioning is a required accommodation,
> use a qualified provider.

## Features

- Live captions from one or more USB microphones
- Operator **Control** window: one card per mic with an on/off toggle and gain slider, plus a live feed
- Optional room-facing **Caption** window for a second screen, projector, or TV
- New microphones are detected automatically when plugged in mid-session
- Transcript saved continuously to a timestamped `.txt` file
- Choice of transcription engine: Whisper (faster-whisper) or Moonshine
- Custom vocabulary: spelling corrections and Whisper prompt hints

## Hardware

Any USB microphone works, including your laptop's built-in mic for testing.

Recommended: **ReSpeaker USB Mic Array (XVF3000)**, a 4-mic array with
360° pickup and about 5 m range. It shows up as a standard audio device
with no drivers. For larger rooms, use one per table on a powered USB hub.

## Setup (macOS)

Requires Python 3.10+ with Tkinter. The python.org installer includes
Tkinter; if you use Homebrew's Python, also run `brew install python-tk`.

```bash
brew install portaudio
pip3 install -r requirements.txt
cp config.example.yaml config.yaml
```

Edit `config.yaml` for your session. Every setting is documented in the file.

If `config.yaml` doesn't exist, CaptionKit automatically falls back to
`config.example.yaml`, so it runs with the recommended baseline settings out
of the box. Copy the example to `config.yaml` when you want to customize
anything; `config.yaml` is git-ignored, so your changes stay local.

## Run

```bash
python3 main.py
```

The first run downloads the selected model, which can take a minute.
Later runs start quickly.

- **Control window**: keep on your laptop. Toggle mics, adjust gain, watch the live feed.
- **Caption window**: drag to the second screen and press **F** for full screen (**Esc** to exit).
  Set `show_caption_window: false` to run with only the Control window.

Stop with Ctrl+C in the terminal or by closing the Control window.

## Configuration highlights

| Setting | What it does |
|---|---|
| `engine` | `whisper` (more accurate, multilingual) or `moonshine` (faster, English only) |
| `model_size` | Whisper size: `tiny`, `base`, `small`, `medium` |
| `chunk_seconds` | Seconds of audio per transcription; higher is more accurate but slower |
| `beam_size` | Whisper decoding width; 1 is fastest |
| `initial_prompt` | Comma-separated list of names/terms to favor (Whisper only). Use a list, not a sentence. |
| `corrections` | Find/replace fixes for words that are consistently mis-heard |
| `mic_names` | Friendly labels for devices, matched by keyword |
| `debug` | Print audio levels and raw engine output to the terminal |

## Tuning tips

- Start with `engine: whisper`, `model_size: base`, `chunk_seconds: 3.0`, `beam_size: 1`.
- If captions are too slow, lower `chunk_seconds` toward 2.0. Going lower hurts accuracy.
- If accuracy is poor and your machine has headroom, try `model_size: small` or `beam_size: 2`.
- Use **gain** to balance mics at different distances from speakers. It amplifies noise
  as well as speech, so it can't rescue a mic that's simply too far away.
- Seeing sentences nobody said? That's Whisper hallucinating on background noise.
  Turn on `debug`, check the audio levels, and make sure `initial_prompt` is a word list.

## Transcript format

```
[10:14 AM] Front Table: Someone said something here
[10:15 AM] Back Left: Response from across the room

--- Microphone connected: Back Right (10:22 AM) ---

[10:22 AM] Back Right: Late arrival joins the conversation
```

## Privacy

- Audio is processed entirely on your device and is never uploaded or stored.
- Transcripts are saved to the path in `config.yaml`. Treat them as meeting
  records, and let attendees know captioning and transcription are running.
- The only network access is the one-time download of speech models.

See [SECURITY.md](SECURITY.md) for how to report a security issue.

## Project layout

```
captionkit/
├── main.py                 entry point
├── config.example.yaml     copy to config.yaml
├── requirements.txt        pinned dependencies
├── pyproject.toml          Ruff and Bandit settings
├── .github/                CI security workflow and Dependabot config
├── core/
│   ├── config.py           loads config.yaml with defaults
│   ├── devices.py          finds mics and watches for hot-plug
│   ├── transcription.py    per-mic capture and the Whisper/Moonshine engines
│   └── session.py          coordinates streams and writes the transcript
└── ui/
    ├── control_window.py   operator panel
    └── caption_window.py   second-screen display
```

## Development

Run the same checks CI runs before opening a pull request:

```bash
pip3 install ruff "bandit[toml]" pip-audit
ruff check .
bandit -c pyproject.toml -r core ui main.py
pip-audit -r requirements.txt
```

## Roadmap

See [NOTES.md](NOTES.md) for known limitations and planned work, including
overlapping audio chunks for better accuracy, Apple Silicon GPU acceleration,
and wireless microphone nodes.

## Contributing

Bug reports, ideas, and pull requests are welcome. Please open an issue first
for larger changes. Feedback from deaf and hard-of-hearing users, and from
anyone who has tried CaptionKit at a real event, is especially valuable.

## Acknowledgements

CaptionKit builds on:

- [Whisper](https://github.com/openai/whisper) by OpenAI
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) by SYSTRAN
- [Moonshine](https://github.com/moonshine-ai/moonshine) by Useful Sensors
- [python-sounddevice](https://github.com/spatialaudio/python-sounddevice)

## License

[MIT](LICENSE) © 2026 Shane Keilson
