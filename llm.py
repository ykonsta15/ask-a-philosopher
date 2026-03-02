import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Tuple

from dotenv import load_dotenv
from openai import OpenAI

from utils import deterministic_index, split_sentences, trim_to_word_limit

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("openai_api_key")
MODEL_NAME = os.getenv("OPENAI_MODEL") or os.getenv("openai_model") or "gpt-5-mini"
REQUEST_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "45"))
TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
TOP_P = float(os.getenv("OPENAI_TOP_P", "0.9"))
PHILOSOPHERS = ("socrates", "plato", "aristotle")
MAX_WORDS = 80


def _build_system_prompt(user_prompt: str) -> str:
    return (
        "You are generating three distinct philosophical responses to a user’s question.\n\n"
        "Return valid JSON only with this exact structure:\n\n"
        "{\n"
        '  "socrates": "string",\n'
        '  "plato": "string",\n'
        '  "aristotle": "string"\n'
        "}\n\n"
        "Global Rules:\n\n"
        "- Each response must be 2–3 sentences total.\n"
        "- Maximum 80 words per response.\n"
        "- Each response must directly address the user’s question.\n"
        "- Do NOT repeat the user’s question verbatim.\n"
        "- Do NOT include bullet points.\n"
        "- Do NOT include labels, markdown, or commentary outside the JSON.\n"
        "- Do NOT mention being an AI.\n"
        "- Each response must contain at least one idea specific to the content of the user’s question.\n"
        "- The three responses must differ meaningfully in reasoning style, not just wording.\n\n"
        "Philosopher Frameworks:\n\n"
        "Socrates:\n"
        "Respond through disciplined questioning and conceptual clarification. Identify hidden assumptions in the question, "
        "examine definitions, and gently challenge what is being taken for granted. Socrates does not rush to give prescriptions; "
        "instead, he seeks clarity about what the person truly means and what they truly value. He often reframes the issue by "
        "asking what the core concept really is (e.g., justice, success, courage, happiness). He may end with one precise, probing "
        "question that exposes a tension or assumption.\n\n"
        "Plato:\n"
        "Respond by elevating the discussion toward ideals, higher principles, and the pursuit of what is truly good, just, or beautiful. "
        "Plato often distinguishes between appearances and deeper reality, and between short-term desires and enduring values. He considers "
        "whether the question aligns with the well-ordered soul and a just life. His tone is reflective and aspirational, guiding the reader "
        "to consider what the highest version of themselves would choose.\n\n"
        "Aristotle:\n"
        "Respond with practical wisdom grounded in virtue ethics and lived experience. Aristotle focuses on habits, character formation, "
        "balance (the golden mean), and cause-and-effect reasoning. He considers what action would cultivate virtue over time and what is "
        "realistically attainable. His tone is measured and pragmatic, emphasizing steady improvement, deliberate choice, and alignment "
        "between goals and conduct.\n\n"
        "If the question is unclear or nonsensical, still respond thoughtfully within these frameworks.\n\n"
        "Return JSON only."
    )


def _response_text(response: Any) -> str:
    direct = getattr(response, "output_text", None)
    if isinstance(direct, str) and direct.strip():
        return direct

    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        for part in getattr(item, "content", []) or []:
            if isinstance(part, dict):
                candidate = part.get("text", "")
            else:
                candidate = getattr(part, "text", "")
            if isinstance(candidate, str) and candidate.strip():
                chunks.append(candidate)
    return "\n".join(chunks).strip()


def _iter_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _iter_strings(v)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)


def _json_candidate_from_blob(blob: str) -> str:
    if not blob:
        return ""
    direct_match = re.search(
        r'\{[\s\S]*"socrates"\s*:\s*"[\s\S]*?"\s*,[\s\S]*"plato"\s*:\s*"[\s\S]*?"\s*,[\s\S]*"aristotle"\s*:\s*"[\s\S]*?"[\s\S]*\}',
        blob,
    )
    if direct_match:
        return direct_match.group(0)

    any_obj = re.search(r"\{[\s\S]*\}", blob)
    return any_obj.group(0) if any_obj else ""


def _validate_payload_dict(data: Dict[str, Any]) -> Dict[str, str]:
    missing = [k for k in PHILOSOPHERS if k not in data]
    if missing:
        raise ValueError(f"Missing keys in JSON payload: {', '.join(missing)}")

    validated: Dict[str, str] = {}
    for key in PHILOSOPHERS:
        value = data.get(key, "")
        if not isinstance(value, str):
            value = str(value)
        value = value.strip()
        if not value:
            raise ValueError(f"Empty value for key: {key}")
        if value.lower() == "string":
            raise ValueError(f"Placeholder value for key: {key}")
        validated[key] = value
    return validated


def _json_objects_from_blob(blob: str) -> list[Dict[str, Any]]:
    decoder = json.JSONDecoder()
    objects: list[Dict[str, Any]] = []
    i = 0
    while i < len(blob):
        if blob[i] != "{":
            i += 1
            continue
        try:
            candidate, end = decoder.raw_decode(blob[i:])
            if isinstance(candidate, dict):
                objects.append(candidate)
            i += max(end, 1)
        except Exception:
            i += 1
    return objects


def _extract_json_from_response(response: Any) -> str:
    primary = _response_text(response)
    candidate = _json_candidate_from_blob(primary)
    if candidate:
        return candidate

    dump = {}
    if hasattr(response, "model_dump"):
        try:
            dump = response.model_dump()
        except Exception:
            dump = {}

    for s in _iter_strings(dump):
        candidate = _json_candidate_from_blob(s)
        if candidate:
            return candidate

    try:
        dump_json = json.dumps(dump, ensure_ascii=True)
    except Exception:
        dump_json = ""

    candidate = _json_candidate_from_blob(dump_json)
    if candidate:
        return candidate

    return primary


def _extract_json(text: str) -> Dict[str, str]:
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return _validate_payload_dict(data)
    except json.JSONDecodeError:
        pass

    objects = _json_objects_from_blob(text)
    last_error: Exception | None = None
    for obj in objects:
        try:
            return _validate_payload_dict(obj)
        except Exception as exc:
            last_error = exc

    if objects and last_error:
        raise ValueError(str(last_error))
    raise ValueError("No JSON object found")


def _repair_json(client: OpenAI, invalid_text: str) -> Tuple[Dict[str, str], str]:
    repair_system = (
        "You repair invalid model output into valid JSON only. "
        "Return exactly one JSON object with keys socrates, plato, aristotle and string values only. "
        "Transform the provided text; do not return a canned template."
    )

    request_kwargs: Dict[str, Any] = {
        "model": MODEL_NAME,
        "max_output_tokens": 300,
        "input": [
            {"role": "system", "content": repair_system},
            {
                "role": "user",
                "content": "Repair this into strict JSON only:\n\n" + invalid_text,
            },
        ],
    }
    if not MODEL_NAME.startswith("gpt-5"):
        request_kwargs["temperature"] = 0
        request_kwargs["top_p"] = 1

    completion = client.responses.create(**request_kwargs)
    repair_raw = _extract_json_from_response(completion)
    return _extract_json(repair_raw), repair_raw


def _enforce_response_limits(philosopher: str, text: str) -> str:
    cleaned = " ".join(text.replace("\n", " ").strip().split())
    sentences = split_sentences(cleaned)

    if len(sentences) > 3:
        sentences = sentences[:3]

    if len(sentences) < 2:
        fallback = {
            "socrates": [
                "Let us define the key term first, because the wording shapes the answer.",
                "Which assumption in the question should be examined before deciding?",
            ],
            "plato": [
                "The strongest answer should align with what is good, just, and true.",
                "Which interpretation remains principled beyond convenience?",
            ],
            "aristotle": [
                "A useful answer connects likely causes to practical consequences.",
                "What concrete next step would test this answer in practice?",
            ],
        }[philosopher]
        while len(sentences) < 2:
            sentences.append(fallback[len(sentences) - 1])

    merged = " ".join(sentences[:3])
    return trim_to_word_limit(merged, MAX_WORDS)


def _coerce_payload(data: Dict[str, str]) -> Dict[str, str]:
    normalized: Dict[str, str] = {}
    for philosopher in PHILOSOPHERS:
        value = data.get(philosopher, "")
        if not isinstance(value, str):
            value = str(value)
        normalized[philosopher] = _enforce_response_limits(philosopher, value)
    return normalized


def _fallback_payload(prompt: str) -> Dict[str, str]:
    topic = " ".join((prompt or "").split())[:120] or "this question"
    variants = {
        "socrates": [
            f"Your question about {topic} turns on the meaning of its central term. Clarify what standard you are using, then test the assumption that currently feels most obvious.",
            f"In {topic}, the first step is to define what would count as a good answer. Which hidden premise in your framing would most change your conclusion if it were false?",
        ],
        "plato": [
            f"For {topic}, the strongest answer is the one aligned with what is good, just, and true over time. Short-term convenience matters less than whether the choice fits your highest principles.",
            f"Regarding {topic}, separate appearances from enduring value before deciding. Ask which option you would still call just and good when immediate pressures fade.",
        ],
        "aristotle": [
            f"With {topic}, connect your reasoning to practical causes and likely consequences. Choose one concrete next step that builds a stable habit, then adjust based on results.",
            f"On {topic}, aim for a balanced response between extremes rather than a perfect theory. Identify the smallest actionable step you can test this week and learn from.",
        ],
    }
    payload: Dict[str, str] = {}
    for philosopher in PHILOSOPHERS:
        options = variants[philosopher]
        idx = deterministic_index(f"{prompt}:{philosopher}:fallback", len(options))
        payload[philosopher] = options[idx]
    return payload


def generate_philosophers_with_meta(prompt: str) -> Tuple[Dict[str, str], Dict[str, Any]]:
    if not API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Set OPENAI_API_KEY in your shell or create "
            f"{ENV_PATH} with OPENAI_API_KEY=..."
        )

    client = OpenAI(api_key=API_KEY, timeout=REQUEST_TIMEOUT_SECONDS)
    meta: Dict[str, Any] = {
        "cache_hit": False,
        "repair_used": False,
        "model": MODEL_NAME,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "raw_json": "",
        "repair_raw_json": "",
    }

    request_kwargs: Dict[str, Any] = {
        "model": MODEL_NAME,
        "max_output_tokens": 650,
        "input": [
            {"role": "system", "content": _build_system_prompt(prompt)},
            {"role": "user", "content": prompt},
        ],
    }
    # Some GPT-5 models in Responses API reject sampling params like temperature/top_p.
    if MODEL_NAME.startswith("gpt-5"):
        request_kwargs["reasoning"] = {"effort": "minimal"}
        request_kwargs["text"] = {"verbosity": "low"}
    else:
        request_kwargs["temperature"] = TEMPERATURE
        request_kwargs["top_p"] = TOP_P

    try:
        completion = client.responses.create(**request_kwargs)
    except Exception as exc:
        raise RuntimeError(
            f"OpenAI request failed (model={MODEL_NAME}). Check API key, billing, and model access. "
            f"Original error: {exc}"
        ) from exc

    no_text = not _response_text(completion).strip()
    incomplete_reason = (
        getattr(getattr(completion, "incomplete_details", None), "reason", None)
        or (
            getattr(completion, "incomplete_details", {}).get("reason")
            if isinstance(getattr(completion, "incomplete_details", None), dict)
            else None
        )
    )
    if no_text and incomplete_reason == "max_output_tokens":
        retry_kwargs = dict(request_kwargs)
        retry_kwargs["max_output_tokens"] = 900
        retry_kwargs["reasoning"] = {"effort": "minimal"}
        retry_kwargs["text"] = {"verbosity": "low"}
        completion = client.responses.create(**retry_kwargs)

    raw = _extract_json_from_response(completion)
    meta["raw_json"] = raw

    try:
        parsed = _extract_json(raw)
    except Exception as first_exc:
        meta["repair_used"] = True
        try:
            parsed, repair_raw = _repair_json(client, raw)
            meta["repair_raw_json"] = repair_raw
        except Exception as repair_exc:
            meta["repair_raw_json"] = f"Repair failed: {repair_exc}"
            parsed = _fallback_payload(prompt)

    return _coerce_payload(parsed), meta


def generate_philosophers(prompt: str) -> Dict[str, str]:
    result, _ = generate_philosophers_with_meta(prompt)
    return result
