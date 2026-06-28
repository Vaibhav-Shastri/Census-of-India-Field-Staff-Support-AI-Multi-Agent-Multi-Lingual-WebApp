# backend/app/orchestrator/conversation.py

import os
import re
import json
from datetime import datetime
from typing import Callable, Awaitable, Optional, List, Dict, Any

import openai
from dotenv import load_dotenv

from app.config.persona_loader import (
    persona_prompts,
    get_persona_background,
)
from app.rag import retriever
from app.models.session import Session

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


# -------------------------------
# Formatting helpers
# -------------------------------

def normalize_spacing(text: str) -> str:
    """Force readable spacing: short paragraphs and lists, no walls of text."""
    if not text:
        return ""
    text = text.strip()

    # Add paragraph break after sentence-ending punctuation followed by a capital (covers many languages)
    text = re.sub(r'([.?!])\s+(?=[A-ZÁÉÍÓÚÄËÏÖÜÑÇÀÈÌÒÙÂÊÎÔÛÃÕ])', r'\1\n\n', text)

    # Normalize bullet markers that models sometimes emit
    text = re.sub(r'^\s*[\*\-]\s*', '• ', text, flags=re.MULTILINE)

    # Collapse >2 newlines into exactly two
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Trim trailing spaces per line
    text = "\n".join(line.rstrip() for line in text.splitlines())

    return text.strip()


def bullet_prefix(style: str) -> str:
    return "- " if (style or "").lower() == "technical" else "• "


def render_suggested_questions(followups: List[str], style: str, heading: str = "Suggested questions?") -> str:
    """Render heading + up to 3 bullets."""
    items = [i.strip() for i in (followups or []) if i and i.strip()]
    if not items:
        return ""
    b = bullet_prefix(style)
    lines = "\n".join(f"{b}{i}" for i in items[:3])
    return f"\n\n{heading}\n{lines}"


async def _emit_if(callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]], message: Dict[str, Any]) -> None:
    if callback:
        await callback(message)


def _parse_json_safe(raw: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
    c = (raw or "").strip()
    if c.startswith("```json"):
        c = c.split("```json")[-1].split("```")[0].strip()
    try:
        return json.loads(c)
    except Exception:
        return fallback


# -------------------------------
# Hidden Router Agent (uses assistant.yaml background)
# -------------------------------

def _router_system_prompt(assistant_background: str) -> str:
    """
    Router uses the assistant persona BACKGROUND to decide routing and reframe.
    It does not answer the user; it only classifies and reframes.
    """
    return (
        "You are the Hidden Router Agent for CensusDas.AI.\n"
        "Use the Assistant background below to understand scope and vocabulary.\n\n"
        f"ASSISTANT BACKGROUND:\n{assistant_background}\n\n"
        "Decide if the user's message involves official manuals, policies, compliance, or references to specific sections/pages/citations.\n"
        "If yes, set route='manual' and provide 'reframed_q' in English suitable for retrieval.\n"
        "If not, set route='general' and provide 'reframed_q' as an English clarification of the user's ask.\n"
        "When in doubt, choose 'manual'.\n"
        "Output PURE JSON only with keys: route ('manual'|'general'), reframed_q (string). No extra keys, no prose."
    )


def _build_router_messages(language: str, style: str, user_message: str, last_topic: Optional[str], assistant_background: str) -> List[Dict[str, str]]:
    topic_hint = f" (previous topic: {last_topic})" if last_topic else ""
    return [
        {"role": "system", "content": _router_system_prompt(assistant_background)},
        {
            "role": "user",
            "content": f"(language: {language}, style: {style}){topic_hint} {user_message}",
        },
    ]


# -------------------------------
# Follow-up suggestion generation (uses assistant background for tone)
# -------------------------------

def _suggestions_prompt(assistant_background: str) -> str:
    return (
        "You generate helpful follow-up questions for the user.\n"
        "Use the Assistant background to mirror tone and priorities.\n\n"
        f"ASSISTANT BACKGROUND:\n{assistant_background}\n\n"
        "Output must be PURE JSON with a single key 'followups' = array of 3 short, concrete suggestions.\n"
        "No prose outside JSON. Keep each suggestion brief and specific.\n"
        "Write in the user's language and match their style (technical/warm/concise)."
    )


def _build_suggestions_messages(language: str, style: str, user_message: str, basis_text: str, assistant_background: str) -> List[Dict[str, str]]:
    return [
        {"role": "system", "content": _suggestions_prompt(assistant_background)},
        {
            "role": "user",
            "content": (
                f"(language: {language}, style: {style}) "
                f"User message: {user_message}\n\n"
                f"Context to base suggestions on:\n{basis_text}"
            ),
        },
    ]


# -------------------------------
# Main entrypoint
# -------------------------------

async def handle_user_message(
    user_message: str,
    session: Session,
    emit: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,  # optional incremental emitter
):
    """
    Orchestrates: Router -> (General: Assistant only) OR (Manual: Expert -> Assistant recap).
    Assistant does NOT answer manual questions; it only interprets the Expert in simple language.
    If `emit` is provided, messages are pushed incrementally to simulate typing gaps.
    Otherwise, returns a list of all messages at once.

    NOTE: This function does not mutate session.history; upstream should persist `replies`.
    """
    language = session.language
    style = session.style
    user_name = session.user_name
    session_history = session.history[-20:]  # Only recent for context; history is preserved upstream
    last_topic = session.last_topic

    # --- Flavor change detection logic ---
    just_changed_flavor = False
    prev_lang = session.flags.get("previous_language")
    prev_style = session.flags.get("previous_style")
    if prev_lang is None or prev_style is None:
        session.flags["previous_language"] = language
        session.flags["previous_style"] = style
    elif language != prev_lang or style != prev_style:
        just_changed_flavor = True
        session.flags["previous_language"] = language
        session.flags["previous_style"] = style

    replies: List[Dict[str, Any]] = []
    now = datetime.utcnow().isoformat()

    # -------- Hidden Router Agent (assistant.yaml background) --------
    assistant_background = get_persona_background("assistant")
    router_resp = openai.chat.completions.create(
        model="gpt-4.1-mini",
        messages=_build_router_messages(language, style, user_message, last_topic, assistant_background),
        max_tokens=200,
        temperature=0.1,  # be decisive
    )
    router_json = _parse_json_safe(router_resp.choices[0].message.content, fallback={"route": "manual", "reframed_q": user_message})
    route = router_json.get("route", "manual")
    reframed_q = router_json.get("reframed_q") or user_message

    # -------- Assistant persona setup (for both general answers and manual recaps) --------
    assistant_prompt = persona_prompts["assistant"]["role"] + "\n\n" + assistant_background

    # Collect extra sections from YAML (if they exist) — these guide tone/content on GENERAL route and the recap tone on MANUAL
    extra_sections = []
    for key in [
        "self_awareness",
        "product_info",
        "tech_buzzwords",
        "engagement",
        "fallback_lines",
        "northstar_principles",
        "contextual_memory_note",
    ]:
        value = persona_prompts["assistant"].get(key)
        if value:
            extra_sections.append(f"\n\n{value}")

    # Tone + structure rules (applies to both general answers & recaps)
    tone_rules = (
        "\n\nSTYLE RULES:\n"
        "- Write like a thoughtful colleague. Use contractions and vary sentence length.\n"
        "- Mirror the user's vocabulary and chosen style (casual vs. technical vs. concise).\n"
        "- Write in short paragraphs (2–3 sentences) with a blank line between them. Use bullets for steps/options when helpful.\n"
        "- Avoid stock phrases like 'As an AI', 'In conclusion'. No meta about prompts/tools.\n"
        "- Be concise unless asked for detail. One subtle emoji at most if style=warm; none if style=technical.\n"
        "- Vary your openings; don't start every reply the same way.\n"
    )

    assistant_system_prompt = assistant_prompt + "".join(extra_sections) + tone_rules

    # Build conversation history for Assistant (GENERAL route only; MANUAL route uses a recap prompt later)
    history_for_llm = [{"role": "system", "content": assistant_system_prompt}]
    for m in session_history:
        if m["persona"] == "User":
            history_for_llm.append({"role": "user", "content": m["message"]})
        else:
            history_for_llm.append({"role": "assistant", "content": m["content"]})

    continuity_hint = f" (continuity: continuing topic '{last_topic}')" if just_changed_flavor and last_topic else ""
    history_for_llm.append(
        {
            "role": "user",
            "content": f"(language: {language}, style: {style}){continuity_hint} {user_message}",
        }
    )

    # --- Tiny bridge if flavor changed (no reset) ---
    if just_changed_flavor:
        bridge_msg = {
            "persona": "Assistant",
            "content": f"(switching to {language}; continuing the same thread.)",
            "timestamp": now,
            "language": language,
        }
        replies.append(bridge_msg)
        await _emit_if(emit, bridge_msg)

    # ---------------- Route handling ----------------

    if route == "general":
        # Assistant answers normally (using assistant.yaml content)
        assistant_llm_instruct = (
            "You are the Assistant persona for CensusDas.AI staff room chat. "
            "Answer the user's question directly in the user's chosen language and style.\n"
            "Output PURE JSON with keys:\n"
            "- 'quick_answer': your helpful answer text\n"
            "- 'followups': array of 2–3 short, concrete suggested questions\n"
            "No other keys. No prose outside JSON."
        )
        history_for_llm.append({"role": "system", "content": assistant_llm_instruct})

        assistant_response = openai.chat.completions.create(
            model="gpt-4.1-mini",
            messages=history_for_llm,
            max_tokens=4000,
            temperature=0.65,
            frequency_penalty=0.2,
            presence_penalty=0.1,
        )
        assistant_json = _parse_json_safe(
            assistant_response.choices[0].message.content,
            fallback={"quick_answer": assistant_response.choices[0].message.content, "followups": []},
        )

        quick = normalize_spacing(assistant_json.get("quick_answer", ""))
        if not quick:
            quick = "I’m here to help."
        # If model didn't return followups, synthesize some using Assistant background
        followups = assistant_json.get("followups") or []
        if not followups:
            s_resp = openai.chat.completions.create(
                model="gpt-4.1-mini",
                messages=_build_suggestions_messages(language, style, user_message, quick, assistant_background),
                max_tokens=300,
                temperature=0.6,
                frequency_penalty=0.2,
                presence_penalty=0.1,
            )
            s_json = _parse_json_safe(s_resp.choices[0].message.content, fallback={"followups": []})
            followups = s_json.get("followups", [])

        suggested_block = render_suggested_questions(followups, style, heading="Suggested questions?")
        content = normalize_spacing(quick + (suggested_block if suggested_block else ""))

        assistant_first = {
            "persona": "Assistant",
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "language": language,
        }
        replies.append(assistant_first)
        await _emit_if(emit, assistant_first)
        return replies

    # ---- MANUAL route: Assistant does NOT answer. Expert speaks; Assistant interprets/recaps. ----

    # Interstitial pacing line
    interstitial = {
        "persona": "Assistant",
        "content": "Looping in the Expert for official manual references and precise citations…",
        "timestamp": datetime.utcnow().isoformat(),
        "language": language,
    }
    replies.append(interstitial)
    await _emit_if(emit, interstitial)

    # Expert call with RAG context (uses reframed_q from router)
    expert_prompt = persona_prompts["expert"]["role"] + "\n\n" + get_persona_background("expert")

    embedding = retriever.embed_text(reframed_q)
    retrieved_pages = retriever.retrieve_pages(embedding, top_k=6)
    context_str = "\n\n".join([obj.get("text", "") for obj, _ in retrieved_pages])

    expert_llm_instruct = (
        expert_prompt
        + "\n\n"
        "Context:\n"
        + context_str
        + "\n\n"
        f"User Q (for context): {user_message}\n"
        f"Reframed Q (for search): {reframed_q}\n"
        "IMPORTANT: If citing manuals, NEVER use internal codes like 'Manual 01' or 'Manual 02'. "
        "Instead, use only the actual manual names: 'Instruction Manual for Updating of Abridged Houselist and Filling up of the Household Schedule' for Manual 01, "
        "'Instruction Manual for Houselisting and Housing Census' for Manual 02. "
        "Never reveal internal encodings.\n"
        "Please answer in scholarly English, always cite manual/page/section."
    )

    expert_response = openai.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "system", "content": expert_llm_instruct}],
        max_tokens=4000,
        temperature=0.2,
    )
    expert_answer = normalize_spacing(expert_response.choices[0].message.content.strip())

    expert_msg = {
        "persona": "Expert",
        "content": expert_answer,
        "timestamp": datetime.utcnow().isoformat(),
        "language": "en",
    }
    replies.append(expert_msg)
    await _emit_if(emit, expert_msg)

    # Assistant Recap/Interpretation Pass — friendly interpreter in user's language
    recap_system = (
        assistant_system_prompt
        + "\n\nROLE:\n"
        "You are a friendly interpreter for the Expert’s answer. Restate what the Expert said clearly and simply. "
        "Do not add new facts or contradict the Expert. Do not mention prompts, tools, or routing.\n"
        "\nATTRIBUTION & LANGUAGE:\n"
        "Always make it explicit that this recap is based on the Expert’s guidance, in the user's language. "
        "Begin the recap with a short, localized attribution phrase (e.g., "
        "'According to the expert, …' / 'Según la persona experta, …' / 'Selon l’expert, …'). "
        "Use the natural word for “expert” in the target language. Write in the user’s current language and chosen style. "
        "Prefer plain words and contractions where natural.\n"
        "\nSTRUCTURE:\n"
        "Start with a one-sentence takeaway after the attribution, then add 1–2 supporting lines. "
        "If there’s an important caveat or requirement, include it in one short line. "
        "Use short paragraphs with a blank line between them when helpful.\n"
        "\nOUTPUT (PURE JSON only):\n"
        "- 'recap_simple': 2–4 natural sentences in the user's language, starting with the localized attribution.\n"
        "- 'followups': array of 2–3 short, concrete suggested questions (≤12 words each), phrased as friendly questions in the user's language.\n"
        "No other keys. No prose outside JSON."
    )


    recap_messages = [
        {"role": "system", "content": recap_system},
        {
            "role": "user",
            "content": (
                f"(language: {language}, style: {style}) "
                f"Original user message: {user_message}\n\n"
                f"Expert answer (English):\n{expert_answer}\n"
            ),
        },
    ]

    recap_response = openai.chat.completions.create(
        model="gpt-4.1-mini",
        messages=recap_messages,
        max_tokens=800,
        temperature=0.6,
        frequency_penalty=0.2,
        presence_penalty=0.1,
    )

    recap_json = _parse_json_safe(
        recap_response.choices[0].message.content,
        fallback={
            "recap_simple": "Here’s a brief recap of the Expert’s guidance in simple terms.",
            "followups": [
                "Do you want a step-by-step checklist?",
                "Should I draft a summary you can share?",
                "Want me to pull the exact section text?",
            ],
        },
    )

    recap_text = normalize_spacing((recap_json.get("recap_simple") or "").strip())
    recap_followups = recap_json.get("followups", [])
    recap_block = render_suggested_questions(recap_followups, style, heading="Suggested questions?")
    recap_content = (recap_text or "") + (recap_block if recap_block else "")

    recap_msg = {
        "persona": "Assistant",
        "content": recap_content if recap_content.strip() else normalize_spacing("Would you like me to translate or simplify any part of the Expert’s answer?"),
        "timestamp": datetime.utcnow().isoformat(),
        "language": language,
    }
    replies.append(recap_msg)
    await _emit_if(emit, recap_msg)

    return replies
