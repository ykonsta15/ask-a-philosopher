import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm import PHILOSOPHERS, generate_philosophers

PROMPTS = [
    "How should I handle conflict with my cofounder about product direction?",
    "Is it ethical to use AI art in a commercial game?",
    "Why do people procrastinate even when they care about the outcome?",
    "Should I move to another city for a higher salary but less community?",
    "What makes a friendship last for decades?",
]


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def main() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set.")

    outputs = []
    for prompt in PROMPTS:
        result = generate_philosophers(prompt)
        outputs.append((prompt, result))

    combined_strings = [
        " | ".join(result[p] for p in PHILOSOPHERS) for _, result in outputs
    ]
    assert len(set(combined_strings)) > 1, "All outputs are identical across prompts."

    for prompt, result in outputs:
        normalized_prompt = _normalize(prompt)
        for philosopher in PHILOSOPHERS:
            normalized_answer = _normalize(result[philosopher])
            assert normalized_prompt not in normalized_answer, (
                f"{philosopher} echoed full prompt verbatim for: {prompt}"
            )

    for philosopher in PHILOSOPHERS:
        variants = {result[philosopher] for _, result in outputs}
        assert len(variants) > 1, f"{philosopher} output is identical across all prompts."

    print("PASS: variation + no verbatim full-prompt echo checks succeeded.")


if __name__ == "__main__":
    main()
