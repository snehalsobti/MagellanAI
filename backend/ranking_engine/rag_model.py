# backend/ranking_engine/rag_model.py
#
# LLM-only ranking pipeline.
#
# Design: pass the FULL course catalog (~237 courses, ~17 K tokens) to the LLM
# in a single call and ask it to return the top-k most relevant course codes.
#
# Why no embedding / dense-retrieval phase:
#   - sentence-transformers + PyTorch consumed ~400 MB RAM and were the root
#     cause of every OOM crash on Render's 512 MB free tier.
#   - GPT-4's language understanding is far richer than a 22 M-parameter
#     mini-model: it identifies relevant courses even when vocabulary differs.
#   - 237 courses × ~70 tokens ≈ 17 K tokens — well within GPT-4.1's 1 M
#     token context window.
#   - Cost delta: ~$0.03–0.05 per call at gpt-4.1 rates — acceptable for a
#     low-traffic demo.

import os
import json
import re
import warnings

import openai
from dotenv import load_dotenv

from backend.data_bridge.interfaces import CatalogBridge

load_dotenv()

# OpenAI settings (set OPENAI_API_KEY in env; RAG_OPENAI_MODEL overrides model)
OPENAI_MODEL = os.getenv("RAG_OPENAI_MODEL", "gpt-4")
OPENAI_TIMEOUT = 45  # seconds — slightly more headroom for larger context
MIN_K = 10
MAX_K = 20
# Max description length per course in the catalog block.  Keeps token count
# manageable while preserving enough context for good matching.
_MAX_DESC_CHARS = 220


def _build_catalog_block(bridge: CatalogBridge) -> tuple[list[str], str]:
    """
    Build a compact, tab-separated text block of ALL rankable courses.
    Year 1/2 baseline courses are excluded (they are pre-selected, not choices).

    Returns:
        all_codes  — list of course codes in catalog order
        block      — multi-line string, one course per line:
                     CODE<tab>Name. Description (truncated)
    """
    docs = bridge.get_rag_documents(active_only=True, exclude_year1_year2=True)
    lines: list[str] = []
    codes: list[str] = []
    for doc in docs:
        code = (doc.course_code or "").strip()
        if not code:
            continue
        name = (doc.title or "").strip()
        desc = (doc.body_text or "").strip()
        if len(desc) > _MAX_DESC_CHARS:
            # Truncate at the last word boundary within the limit
            desc = desc[:_MAX_DESC_CHARS].rsplit(" ", 1)[0] + "…"
        detail = ". ".join(filter(None, [name, desc]))
        lines.append(f"{code}\t{detail}")
        codes.append(code)
    return codes, "\n".join(lines)


def rag_model(
    user_prompt: str,
    k: int = 10,
    retrieval_k: int | None = None,
    bridge: CatalogBridge | None = None,
) -> list[str]:
    """
    LLM-only course ranking.

    Sends the full course catalog to GPT-4 and asks it to return the k most
    relevant course codes as a JSON array, most relevant first.

    Args:
        user_prompt  — free-text description of student interests / goals
        k            — number of courses to return (clamped to [MIN_K, MAX_K])
        retrieval_k  — ignored (kept so existing callers don't break)
        bridge       — CatalogBridge instance (required)

    Returns:
        List of up to k course code strings.  Falls back to the first k courses
        in catalog order if the LLM call fails.
    """
    if retrieval_k is not None:
        warnings.warn(
            "rag_model: retrieval_k is no longer used (the pipeline is LLM-only). "
            "Remove this argument from the caller to suppress this warning.",
            DeprecationWarning,
            stacklevel=2,
        )

    if not isinstance(user_prompt, str) or not user_prompt.strip():
        return []

    k = max(MIN_K, min(MAX_K, int(k)))

    if bridge is None:
        raise ValueError("CatalogBridge is required for rag_model")

    all_codes, catalog_block = _build_catalog_block(bridge)
    if not all_codes:
        return []

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to your environment before calling rag_model."
        )

    system_message = (
        "You are a course recommendation assistant for ECE students at the University of Toronto. "
        "Given a student's interests and a full course catalog, return a JSON array of course codes "
        "ranked from most to least relevant to the student's request. "
        "If the student explicitly names a course code (e.g. 'ECE421H1'), prioritise it if it "
        "appears in the catalog. "
        "Output ONLY a valid JSON array like [\"ECE421H1\", \"ECE358H1\"] — no explanation, "
        "no extra text, no markdown."
    )

    user_message = (
        f"Student interests:\n{user_prompt}\n\n"
        f"Course catalog (CODE<tab>Name. Description):\n{catalog_block}\n\n"
        f"Return a JSON array of exactly {k} course codes, most relevant first."
    )

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user",   "content": user_message},
    ]

    raw = ""
    try:
        client = openai.OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.0,
            max_tokens=512,
            timeout=OPENAI_TIMEOUT,
        )
        raw = (resp.choices[0].message.content or "").strip()
        print(f"[RAG] LLM returned: {raw[:120]}...")
    except Exception as exc:
        print(f"[RAG] LLM call failed — falling back to catalog order. Error: {exc}")
        return all_codes[:k]

    # Parse JSON array from raw response (handle minor formatting noise)
    parsed = None
    try:
        parsed = json.loads(raw)
    except Exception:
        m = re.search(r"(\[.*?\])", raw, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(1))
            except Exception:
                pass

    code_set = set(all_codes)
    if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
        validated: list[str] = []
        for code in parsed:
            if code in code_set and code not in validated:
                validated.append(code)
        # Pad to k with catalog-order courses the LLM didn't include
        if len(validated) < k:
            for c in all_codes:
                if c not in validated:
                    validated.append(c)
                if len(validated) >= k:
                    break
        return validated[:k]

    # Fallback: catalog order
    print("[RAG] Could not parse LLM response — falling back to catalog order.")
    return all_codes[:k]


if __name__ == "__main__":
    prompt = input("Describe your interests and goals: ").strip()
    if prompt:
        try:
            results = rag_model(prompt, k=20)
            print(results)
        except Exception as e:
            print("Error:", str(e))
    else:
        print("No prompt provided.")
