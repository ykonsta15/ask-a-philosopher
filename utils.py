import hashlib
import re


_SENTENCE_REGEX = re.compile(r"[^.!?]+[.!?]|[^.!?]+$")


def sanitize_input(text: str) -> str:
    return (text or "").strip()


def stable_hash(text: str) -> int:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def deterministic_index(seed_text: str, size: int) -> int:
    if size <= 0:
        raise ValueError("size must be positive")
    return stable_hash(seed_text) % size


def split_sentences(text: str) -> list[str]:
    matches = _SENTENCE_REGEX.findall(text.strip())
    return [" ".join(m.strip().split()) for m in matches if m.strip()]


def trim_to_word_limit(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]).rstrip(" ,;:") + "."
