"""
Configuration loader.
Reads config.yaml from the project directory. If config.yaml doesn't exist,
falls back to config.example.yaml (the committed template) so a fresh clone
runs with the tuned baseline settings instead of bare built-in defaults.
All fields have sensible defaults so a minimal config file still works.
"""

import os

import yaml

DEFAULTS = {
    "model_size": "small",
    "output_path": "~/Desktop/captionkit_transcript.txt",
    "font_size": 36,
    "mic_names": {},
    "corrections": {},
    "initial_prompt": None,
    "debug": False,
    "show_caption_window": True,
}

# Fields that should fall back to {} (not None) when present but empty in YAML
DICT_FIELDS = ["mic_names", "corrections"]


def load_config(path="config.yaml"):
    config = dict(DEFAULTS)

    # Fallback: if config.yaml is missing (e.g. a fresh clone, since config.yaml
    # is git-ignored), load config.example.yaml from the same folder instead.
    if not os.path.exists(path):
        example = os.path.join(os.path.dirname(path), "config.example.yaml")
        if os.path.exists(example):
            print(f"[config] No {path} found — using {example}. "
                  f"Copy it to config.yaml to customize.")
            path = example

    if os.path.exists(path):
        try:
            with open(path) as f:
                user_config = yaml.safe_load(f) or {}
            # An empty/commented-out dict field (e.g. "mic_names:") loads as
            # None in YAML — normalize that to {} so .items() etc. work.
            for field in DICT_FIELDS:
                if user_config.get(field) is None and field in user_config:
                    user_config[field] = {}
            config.update(user_config)
            print(f"[config] Loaded from {path}")
        except Exception as e:
            print(f"[config] Error reading {path}: {e} — using defaults")
    else:
        print("[config] No config.yaml or config.example.yaml found — using built-in defaults")
    return config
