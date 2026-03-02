from typing import Dict

from utils import deterministic_index

_VARIANTS = {
    "socrates": {
        "openers": [
            "Start by defining the key terms clearly.",
            "Question the assumption hidden in the framing.",
            "Clarify what exactly is being asked first.",
            "Separate certainty from appearance before concluding.",
            "Test whether the premise is truly necessary.",
        ],
        "closers": [
            "Probe the strongest counterexample.",
            "Refine the central definition once more.",
            "Check what evidence would change your view.",
            "Identify the first assumption to challenge.",
            "Aim for clarity before commitment.",
        ],
    },
    "plato": {
        "openers": [
            "Frame it by what is good, just, and true.",
            "Lift the question from convenience to principle.",
            "Consider the ideal the answer should serve.",
            "Judge the claim by enduring values.",
            "Ask which view aligns with justice and truth.",
        ],
        "closers": [
            "Prefer coherence over short-term gain.",
            "Keep the higher aim in view.",
            "Test fairness, not just usefulness.",
            "Choose what remains right in hindsight.",
            "Anchor the answer in principle.",
        ],
    },
    "aristotle": {
        "openers": [
            "Link causes to practical consequences.",
            "Balance outcomes with virtue in action.",
            "Move from theory to a testable step.",
            "Aim for the mean between extremes.",
            "Focus on habits that can be repeated.",
        ],
        "closers": [
            "Name one concrete next step.",
            "Choose a repeatable action this week.",
            "Keep the tradeoff explicit and practical.",
            "Refine the answer through practice.",
            "Build a habit, then evaluate results.",
        ],
    },
}


def get_style_hints(user_prompt: str, philosopher: str) -> Dict[str, str]:
    key = philosopher.lower().strip()
    if key not in _VARIANTS:
        raise ValueError(f"Unknown philosopher: {philosopher}")

    bank = _VARIANTS[key]
    opener_idx = deterministic_index(f"{user_prompt}:{key}:opener", len(bank["openers"]))
    closer_idx = deterministic_index(f"{user_prompt}:{key}:closer", len(bank["closers"]))

    return {
        "opener": bank["openers"][opener_idx],
        "closer": bank["closers"][closer_idx],
    }
