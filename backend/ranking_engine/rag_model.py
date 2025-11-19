# backend/ranking_engine/rag_model.py

from pathlib import Path
import os
import json
import re
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import openai
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file if present

# Config
# data folder is in the parent of backend which is parent of ranking_engine
DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "courses_description.ods"
CACHE_DIR = Path(".rag_cache")
EMB_FILE = CACHE_DIR / "course_embeddings.npy"
CODES_FILE = CACHE_DIR / "course_codes.npy"
TEXTS_FILE = CACHE_DIR / "course_texts.npy"
MODEL_NAME = "all-MiniLM-L6-v2"
MIN_K = 10
MAX_K = 20

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


def read_courses(path: Path):
    """
    Read the ODS file and return a DataFrame with columns:
    'Course Code', 'Course Name', 'Description'
    """
    if not path.exists():
        raise FileNotFoundError(f"{path} does not exist.")
    try:
        df = pd.read_excel(path, engine="odf")
    except Exception:
        df = pd.read_excel(path)
    df.columns = [str(c).strip() for c in df.columns]
    expected = ["Course Code", "Course Name", "Description"]
    if not all(col in df.columns for col in expected):
        raise ValueError(f"Expected columns {expected} in {path}, got {list(df.columns)}")
    df = df.dropna(subset=["Course Code"])
    df["Course Name"] = df["Course Name"].fillna("")
    df["Description"] = df["Description"].fillna("")
    df["Course Code"] = df["Course Code"].astype(str)
    return df.reset_index(drop=True)


def prepare_texts(df: pd.DataFrame):
    texts = (df["Course Name"].str.strip() + ". " + df["Description"].str.strip()).tolist()
    texts = [t if t.strip() != "" else df.loc[i, "Course Code"] for i, t in enumerate(texts)]
    return texts


def build_or_load_index(data_path: Path = DATA_PATH):
    """
    Builds embeddings from the .ods file and caches them.
    Returns: course_codes (list[str]), texts (list[str]), embeddings (np.ndarray)
    """
    CACHE_DIR.mkdir(exist_ok=True)
    if EMB_FILE.exists() and CODES_FILE.exists() and TEXTS_FILE.exists():
        embeddings = np.load(EMB_FILE)
        codes = np.load(CODES_FILE, allow_pickle=True).tolist()
        texts = np.load(TEXTS_FILE, allow_pickle=True).tolist()
        return codes, texts, embeddings

    df = read_courses(data_path)
    texts = prepare_texts(df)
    codes = df["Course Code"].tolist()
    model = get_model()
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True, normalize_embeddings=True)
    np.save(EMB_FILE, embeddings)
    np.save(CODES_FILE, np.array(codes, dtype=object))
    np.save(TEXTS_FILE, np.array(texts, dtype=object))
    return codes, texts, embeddings


def get_relevant_courses(user_prompt: str, k: int = 10, data_path: Path = DATA_PATH):
    """
    Dense-retrieval: Given a prompt, return top-k course codes by embedding similarity.
    k is clamped to [MIN_K, MAX_K].
    """
    if not isinstance(user_prompt, str) or user_prompt.strip() == "":
        return []

    k = int(k)
    k = max(MIN_K, min(MAX_K, k))

    codes, texts, embeddings = build_or_load_index(data_path)
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
        "number of items. DO NOT include any additional text, explanation, or punctuation outside the JSON array."
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
            # No requests available either — raise a clear error including the original exception
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


def rag_model(user_prompt: str, k: int = 10, retrieval_k: int = None, data_path: Path = DATA_PATH):
    """
    Full RAG pipeline:
      1. Dense-retrieval to get candidate courses (retrieval_k).
      2. Pass candidates + user prompt to ChatGPT to produce a final ranked list (JSON array).
      3. Parse and return Python list[str] of course codes in descending relevance.

    Parameters:
      - user_prompt: user interests/goals (string)
      - k: number of results to return (clamped to [MIN_K, MAX_K])
      - retrieval_k: number of candidates to send to the LLM (defaults to MAX_K)
    """
    if not isinstance(user_prompt, str) or user_prompt.strip() == "":
        return []

    k = int(k)
    k = max(MIN_K, min(MAX_K, k))
    retrieval_k = retrieval_k or max(MAX_K, k)

    # Step 1: retrieval (we retrieve retrieval_k candidates)
    codes_all, texts_all, embeddings = build_or_load_index(data_path)
    if len(codes_all) == 0:
        return []

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
        # If ChatGPT call fails (missing key, network, etc), provide clear debug info and fall back
        # to dense-retrieval order so the function still returns results.
        # For debugging locally, raise the error instead of silently falling back:
        # raise
        # Fallback return:
        print(f"Warning: ChatGPT call failed, falling back to dense retrieval. Error: {e}")
        return candidate_codes[:k]

    # Step 3: parse JSON out of raw response
    raw = raw.strip()
    parsed = None
    # Try direct JSON parse
    try:
        parsed = json.loads(raw)
    except Exception:
        # Try to extract first JSON array in text
        m = re.search(r"(\[.*\])", raw, re.S)
        if m:
            try:
                parsed = json.loads(m.group(1))
            except Exception:
                parsed = None

    # Validate parsed result: must be list of strings (course codes)
    if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
        # Truncate/pad to k
        return parsed[:k]
    # Fallback: return retrieval-only codes
    return candidate_codes[:k]

if __name__ == "__main__":
    prompt = input("Describe your interests and goals: ").strip()
    if prompt:
        try:
            results = rag_model(prompt, k=10)
            print(results)
        except Exception as e:
            print("Error:", str(e))
    else:
        print("No prompt provided.")