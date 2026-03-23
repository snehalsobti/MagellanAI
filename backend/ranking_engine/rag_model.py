# backend/ranking_engine/rag_model.py

from pathlib import Path
import os
import json
import re
import hashlib
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import openai
from dotenv import load_dotenv
from backend.data_bridge.interfaces import CatalogBridge
load_dotenv()  # Load environment variables from .env file if present

# Config
CACHE_DIR = Path(".rag_cache")
EMB_FILE = CACHE_DIR / "course_embeddings.npy"
CODES_FILE = CACHE_DIR / "course_codes.npy"
TEXTS_FILE = CACHE_DIR / "course_texts.npy"
FINGERPRINT_FILE = CACHE_DIR / "catalog_fingerprint.txt"
MODEL_NAME = "all-MiniLM-L6-v2"
MIN_K = 10
MAX_K = 20

# Bump this string whenever the content fed to the embedding model changes (e.g. a
# new field is added to the embedded text, or year1/year2 filtering is toggled).
# A changed version causes the fingerprint to differ from any cached value, forcing
# a full index rebuild so stale embeddings are never used.
_EMBEDDING_SCHEMA_VERSION = "v2"

# OpenAI Chat settings (set OPENAI_API_KEY in env)
OPENAI_MODEL = os.getenv("RAG_OPENAI_MODEL", "gpt-4")
OPENAI_TIMEOUT = 30  # seconds

# Initialize model (lazy load)
_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def read_courses_from_bridge(bridge: CatalogBridge):
    # Year 1/2 courses are pre-requisites already known; excluding them prevents the
    # ranking engine from recommending them as profile choices.
    docs = bridge.get_rag_documents(active_only=True, exclude_year1_year2=True)
    data = {
        "Course Code": [d.course_code for d in docs],
        "Course Name": [d.title for d in docs],
        "Description": [d.body_text for d in docs],
    }
    return pd.DataFrame(data).reset_index(drop=True)


def prepare_texts(df: pd.DataFrame):
    """
    Build the text fed to the embedding model for each course.

    Format: "COURSE_CODE. Course Name. Description"

    Prepending the course code means that if a user explicitly mentions a code
    (e.g. "ECE421H1") in their prompt, the cosine similarity will pick it up in
    Phase 1 — not just semantically via the name/description.
    """
    texts: list[str] = []
    for i in range(len(df)):
        code = str(df.loc[i, "Course Code"]).strip()
        name = str(df.loc[i, "Course Name"]).strip()
        desc = str(df.loc[i, "Description"]).strip()
        # Always start with the course code so exact-code queries match directly.
        parts = [code]
        if name:
            parts.append(name)
        if desc:
            parts.append(desc)
        texts.append(". ".join(parts))
    return texts


def _get_fingerprint(bridge: CatalogBridge) -> str:
    # Include schema version so any change to prepare_texts or index filters
    # automatically busts the cached embeddings.
    raw = f"schema:{_EMBEDDING_SCHEMA_VERSION}:bridge:{bridge.get_catalog_fingerprint()}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def build_or_load_index(bridge: CatalogBridge):
    """
    Builds embeddings from bridge documents and caches them.
    Returns: course_codes (list[str]), texts (list[str]), embeddings (np.ndarray)
    """
    CACHE_DIR.mkdir(exist_ok=True)
    current_fingerprint = _get_fingerprint(bridge)
    cache_fingerprint = FINGERPRINT_FILE.read_text().strip() if FINGERPRINT_FILE.exists() else None
    if (
        EMB_FILE.exists()
        and CODES_FILE.exists()
        and TEXTS_FILE.exists()
        and cache_fingerprint == current_fingerprint
    ):
        embeddings = np.load(EMB_FILE)
        codes = np.load(CODES_FILE, allow_pickle=True).tolist()
        texts = np.load(TEXTS_FILE, allow_pickle=True).tolist()
        return codes, texts, embeddings

    df = read_courses_from_bridge(bridge)
    texts = prepare_texts(df)
    codes = df["Course Code"].tolist()
    model = get_model()
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True, normalize_embeddings=True)
    np.save(EMB_FILE, embeddings)
    np.save(CODES_FILE, np.array(codes, dtype=object))
    np.save(TEXTS_FILE, np.array(texts, dtype=object))
    FINGERPRINT_FILE.write_text(current_fingerprint)
    return codes, texts, embeddings


def get_relevant_courses(user_prompt: str, k: int = 10, bridge: CatalogBridge | None = None):
    """
    Dense-retrieval: Given a prompt, return top-k course codes by embedding similarity.
    k is clamped to [MIN_K, MAX_K].
    """
    if not isinstance(user_prompt, str) or user_prompt.strip() == "":
        return []

    k = int(k)
    k = max(MIN_K, min(MAX_K, k))

    if bridge is None:
        raise ValueError("CatalogBridge is required for get_relevant_courses")
    codes, texts, embeddings = build_or_load_index(bridge)
    if len(codes) == 0:
        return []

    model = get_model()
    q_emb = model.encode([user_prompt], convert_to_numpy=True, normalize_embeddings=True)
    sims = (embeddings @ q_emb[0]).reshape(-1)
    top_idx = np.argsort(-sims)[:k]
    top_codes = [codes[int(i)] for i in top_idx]
    return top_codes


# ----- RAG wrapper using ChatGPT API to synthesize / rerank and enforce JSON-only output -----
def _build_candidates_block(codes: list[str], texts: list[str]) -> str:
    """
    Build a text block listing candidates with code, name+description (texts aligned to codes).
    texts list must align index-wise with codes.
    """
    lines = []
    for c, t in zip(codes, texts):
        # Keep each candidate compact to fit prompt token limits
        snippet = t.replace("\n", " ").strip()
        lines.append(f"{c}\t{snippet}")
    return "\n".join(lines)


def call_chatgpt_system(user_prompt: str, candidates_block: str, desired_k: int) -> str:
    """
    Call OpenAI ChatCompletion (ChatGPT) and return raw assistant content.
    Re-reads OPENAI_API_KEY from environment at call time, tries openai package first,
    then falls back to a direct requests call if openai isn't installed.

    Raises RuntimeError with a clear message if the API key is missing or the API call fails.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set in environment. Set it before calling rag_model.")

    system_message = (
        "You are an assistant that, given a user request and a list of candidate courses (one per line, each "
        "line: COURSE_CODE <tab> CourseName. Description), must return a JSON array (Python list) of course codes "
        "only, ordered from most to least relevant to the user's request. The array must contain at most the requested "
        "number of items. If the user explicitly mentions a course code (e.g. 'ECE421H1'), treat that as a strong "
        "signal and prioritise that course near the top of the ranking if it appears in the candidates. "
        "DO NOT include any additional text, explanation, or punctuation outside the JSON array."
        " Output must be valid JSON like [\"ACT230H1\", \"MAT137Y1\", ...]."
    )

    user_message = (
        f"User request:\n{user_prompt}\n\n"
        f"Candidate courses (one per line):\n{candidates_block}\n\n"
        f"Return a JSON array of up to {desired_k} course codes only, ranked most relevant first."
    )

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
    ]

    # Try using the openai package if available
    try:
        openai.api_key = api_key
        resp = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.0,
            max_tokens=512,
            timeout=OPENAI_TIMEOUT,
        )
        return resp["choices"][0]["message"]["content"]
    except Exception as e_openai:
        # If import exists but call failed or package missing, attempt HTTP fallback using requests
        try:
            import requests
        except Exception:
            # No requests available either - raise a clear error including the original exception
            raise RuntimeError(
                "OpenAI package call failed and 'requests' is not available for fallback. "
                f"OpenAI error: {e_openai}"
            ) from e_openai

        # Prepare REST call
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": OPENAI_MODEL,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": 512,
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=OPENAI_TIMEOUT)
        except Exception as e_req:
            raise RuntimeError(f"HTTP request to OpenAI failed: {e_req}") from e_req

        if resp.status_code != 200:
            # include response text for debugging but do not leak full key
            raise RuntimeError(f"OpenAI API error: {resp.status_code} - {resp.text}")

        j = resp.json()
        try:
            return j["choices"][0]["message"]["content"]
        except Exception as e_parse:
            raise RuntimeError(f"Unexpected OpenAI response structure: {j}") from e_parse


def rag_model(
    user_prompt: str,
    k: int = 10,
    retrieval_k: int = None,
    bridge: CatalogBridge | None = None,
):
    """
    Full RAG pipeline:
      1. Dense-retrieval to get candidate courses (retrieval_k).
      2. Pass candidates + user prompt to ChatGPT to produce a final ranked list (JSON array).
      3. Parse, validate (only from candidates), pad with retrieval results if needed, and return exactly k course codes.

    Behavior:
      - k is clamped to [MIN_K, MAX_K].
      - By default retrieval_k = 3 * k (capped to the number of available courses).
      - The LLM is asked to return at most k items. Final returned list is exactly k items (or fewer if dataset smaller).
    """
    if not isinstance(user_prompt, str) or user_prompt.strip() == "":
        return []

    # clamp k
    k = int(k)
    k = max(MIN_K, min(MAX_K, k))

    if bridge is None:
        raise ValueError("CatalogBridge is required for rag_model")

    # Load index
    codes_all, texts_all, embeddings = build_or_load_index(bridge)
    if len(codes_all) == 0:
        return []

    # Default retrieval_k = 3 * k (cap to available items). If caller provided retrieval_k, use it (clamped).
    if retrieval_k is None:
        retrieval_k = min(len(codes_all), 3 * k)
    else:
        retrieval_k = max(1, min(len(codes_all), int(retrieval_k)))

    # Step 1: retrieval
    model = get_model()
    q_emb = model.encode([user_prompt], convert_to_numpy=True, normalize_embeddings=True)
    sims = (embeddings @ q_emb[0]).reshape(-1)
    top_idx = np.argsort(-sims)[:retrieval_k]
    candidate_codes = [codes_all[int(i)] for i in top_idx]
    candidate_texts = [texts_all[int(i)] for i in top_idx]

    # Build candidate block for prompt
    candidates_block = _build_candidates_block(candidate_codes, candidate_texts)
 
    # Step 2: call ChatGPT to rerank/synthesize and produce strict JSON array
    try:
        raw = call_chatgpt_system(user_prompt, candidates_block, k)
    except Exception as e:
        # Fallback to dense retrieval order if LLM call fails
        print(f"Warning: ChatGPT call failed, falling back to dense retrieval. Error: {e}")
        # If dataset smaller than k, return up to available items
        return candidate_codes[:min(k, len(candidate_codes))]

    # Step 3: parse JSON out of raw response and validate
    raw = (raw or "").strip()
    parsed = None
    try:
        parsed = json.loads(raw)
    except Exception:
        m = re.search(r"(\[.*\])", raw, re.S)
        if m:
            try:
                parsed = json.loads(m.group(1))
            except Exception:
                parsed = None

    # Validate parsed result: must be list of strings and drawn from candidate_codes
    if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
        validated = []
        candidate_set = set(candidate_codes)
        for code in parsed:
            if code in candidate_set and code not in validated:
                validated.append(code)
        # Pad with retrieval-order candidates if LLM provided fewer than k valid items
        if len(validated) < k:
            for c in candidate_codes:
                if c not in validated:
                    validated.append(c)
                if len(validated) >= k:
                    break
        # Ensure we don't return more than available courses
        return validated[:min(k, len(candidate_codes))]

    # Fallback: return retrieval-only codes (clamped to k or available count)
    return candidate_codes[:min(k, len(candidate_codes))]

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