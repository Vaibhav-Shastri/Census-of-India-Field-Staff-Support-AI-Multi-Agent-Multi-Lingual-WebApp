# backend/app/config/persona_loader.py

import os
import yaml

PERSONA_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "persona_prompts")

# Feature flag: disable assistant greetings everywhere by default.
# Set DISABLE_ASSISTANT_GREETING=0 to re-enable.
DISABLE_ASSISTANT_GREETING = os.getenv("DISABLE_ASSISTANT_GREETING", "1") == "1"


def load_all_personas():
    """Load all persona YAML files from persona_prompts/ into a dict."""
    prompts = {}
    if not os.path.isdir(PERSONA_PROMPTS_DIR):
        return prompts

    for fname in os.listdir(PERSONA_PROMPTS_DIR):
        if not fname.endswith(".yaml"):
            continue
        key = fname.replace(".yaml", "")
        path = os.path.join(PERSONA_PROMPTS_DIR, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            data = {}
        prompts[key] = data
    return prompts


persona_prompts = load_all_personas()


def _assistant_node():
    return (persona_prompts.get("assistant") or {})


def get_assistant_flavors():
    """
    Return assistant flavor list. If greetings are disabled, strip any 'greeting'
    field so frontends can't accidentally render it.
    """
    assistant = _assistant_node()
    flavors = (assistant.get("flavors") or [])
    if not isinstance(flavors, list):
        return []

    if DISABLE_ASSISTANT_GREETING:
        sanitized = []
        for f in flavors:
            if isinstance(f, dict):
                f2 = dict(f)
                f2.pop("greeting", None)
                sanitized.append(f2)
        return sanitized

    return flavors


def get_assistant_greeting(language: str, style: str) -> str:
    """
    Return the greeting for a specific flavor, or empty string when greetings are disabled.
    """
    if DISABLE_ASSISTANT_GREETING:
        return ""

    # When enabled, try to find a matching flavor greeting.
    for flavor in get_assistant_flavors():
        if (
            isinstance(flavor, dict)
            and flavor.get("language") == language
            and flavor.get("style") == style
        ):
            return str(flavor.get("greeting", "") or "")

    # Fallback to sample_lines[0] if present, else empty.
    assistant = _assistant_node()
    sample_lines = assistant.get("sample_lines") or []
    if isinstance(sample_lines, list) and sample_lines:
        return str(sample_lines[0] or "")
    return ""


def get_persona_background(persona: str) -> str:
    """Return the 'background' string for a given persona, or empty if missing."""
    node = (persona_prompts.get(persona) or {})
    return str(node.get("background", "") or "")
