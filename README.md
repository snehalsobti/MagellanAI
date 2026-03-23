# MagellanAI

An intelligent course-planning assistant for upper-year Electrical and Computer Engineering (ECE) students at the University of Toronto. MagellanAI accepts a student's interests in plain English, then automatically generates a complete, valid, and personalized 10-credit Year 3/4 course profile that satisfies every ECE graduation requirement. Once a profile is generated, students can iteratively refine it by locking, excluding, liking, or disliking individual courses and regenerating with those preferences enforced.

---

## Table of Contents

1. [How It Works](#how-it-works)
2. [Interactive Feedback Loop](#interactive-feedback-loop)
3. [Project Structure](#project-structure)
4. [Quick Start](#quick-start)
5. [Database Management](#database-management)
6. [API Reference](#api-reference)
7. [Testing](#testing)
8. [ECE Program Constraints - Single Source of Truth](#ece-program-constraints--single-source-of-truth)
9. [Architecture Notes](#architecture-notes)
10. [Troubleshooting](#troubleshooting)
11. [README Maintenance](#readme-maintenance)
12. [Contributors](#contributors)

---

## How It Works

### Initial profile generation

```
User interests (text)
      ↓
POST /generate-profile
      ↓
RAG Model  ──  semantic search (sentence-transformers) + GPT-4 reranking
      │         → ranked list of relevant course codes
      │         (Year 1/2 courses excluded from the ranking index)
      ↓
Profile Generator (CP-SAT solver, 8 s timeout)
      │         → feasible 10-credit semester plan satisfying all constraints
      ↓
Constraint Verifier  ──  double-checks every ECE rule
      ↓
Response  ──  semester plan, requirement buckets, CEAB summary, stats
```

### Iterative refinement (feedback loop)

```
User applies feedback to any course slot
  (LOCK / EXCLUDE / LIKE / DISLIKE)
      ↓
POST /regenerate-profile
      ↓
Profile Generator (CP-SAT solver, 15 s timeout)
      │  LOCK / EXCLUDE → hard constraints added to the CP-SAT model
      │  LIKE           → soft positive weight (+100) in objective
      │  DISLIKE        → soft negative weight (-100) in objective
      ↓
Constraint Verifier
      ↓
Response  ──  updated semester plan + FeedbackHonorReport
             (which liked/disliked courses were honoured or overridden)
```

**Key properties of the generated profile:**
- Exactly 20 semester slots across 3F / 3S / 4F / 4S (5 per semester)
- 19 unique course codes → 10.0 credits (18 × 0.5 H-courses + 1 × 1.0 Y capstone)
- All ECE breadth, depth, CEAB, complementary, and elective rules enforced as hard constraints
- Student preferences are a soft objective — maximised within the feasible region

---

## Interactive Feedback Loop

### Overview

After a profile is first generated, MagellanAI enters an iterative mode. The user can mark any course slot with one of four feedback states, then click **"Regenerate with Feedback"** to produce a new profile that respects those signals. The profile and its feedback history are stored in-memory for the session.

### Feedback states

| State | Symbol | CP-SAT treatment | Effect |
|---|---|---|---|
| **LOCK** | 🔒 | Hard constraint: `y[code] == 1` | Course must appear in the new profile |
| **EXCLUDE** | ❌ | Hard constraint: `y[code] == 0` | Course must not appear in the new profile |
| **LIKE** | 👍 | Soft objective: `+100 × y[code]` | Course strongly preferred; may still be omitted if constraints prevent it |
| **DISLIKE** | 👎 | Soft objective: `−100 × y[code]` | Course penalised; may still appear if it is required by hard constraints |

Only one state can be active per slot at a time. Selecting a new state replaces the previous one. Selecting the active state again clears it.

### Capstone handling

A capstone course (ECE496Y1, APS490Y1, or BME498Y1) occupies two semester slots (4F and 4S) but is a single course code. Applying any feedback state to either slot automatically applies it to both — the backend keyed on course code ensures symmetry without any frontend duplication.

### Regeneration behaviour

- **Timeout**: The CP-SAT solver has a **15-second** time limit for regeneration calls (compared to 8 seconds for initial generation). If the solver cannot find a feasible solution in time, the backend returns `{ success: false, timed_out: true }` and the current profile is preserved in the frontend unchanged.
- **Infeasibility**: If the feedback constraints make the problem infeasible (e.g. LOCK + EXCLUDE on the same course, or all capstone codes excluded), the backend returns `{ success: false, feedback_infeasible: true }`. The current profile is preserved.
- **Conflict validation**: The `/regenerate-profile` endpoint pre-validates obvious conflicts (LOCK vs EXCLUDE on the same course, excluding required courses, excluding all capstones) before invoking the solver, returning a structured error immediately.

### Honor report

After a successful regeneration the response includes a `feedback_result` (type `FeedbackHonorReport`) explaining what happened to each soft-feedback course:

| Field | Meaning |
|---|---|
| `liked_honored` | Liked courses that were placed in the new profile |
| `liked_skipped` | Liked courses that could not be placed (constraint conflict) |
| `disliked_honored` | Disliked courses that were successfully kept out of the profile |
| `disliked_forced` | Disliked courses that still appeared (required by hard constraints) |

### Feedback carry-forward

After each regeneration the previous feedback is **carried forward** into the new iteration rather than cleared. This means the user can see which constraints are still active, remove individual entries from the Feedback Memory Panel, change states via the gear icon, or clear everything with the "Clear all" button. Feedback that was applied to excluded courses (which no longer appear in the grid) remains visible in the panel using a session-local course-name cache.

### Session history

- Up to **10 past iterations** are stored in-memory and accessible via a history dropdown.
- Past iterations are read-only: the semester plan grid shows the feedback tints that were active at that time, and the Feedback Memory Panel shows those entries (no editing).
- No backend persistence is involved — history is lost on page refresh. The data structures are designed to be database-persisted in a future iteration with minimal refactoring.

### Rate limiting

Both `/generate-profile` and `/regenerate-profile` share the same in-memory rate-limiter bucket: **8 requests per 60 seconds per IP**.

---

## Project Structure

```
MagellanAI/
├── api_server.py                          # FastAPI server - all HTTP endpoints
├── requirements.txt                       # Base Python dependencies
├── requirements_api.txt                   # API-server-specific dependencies
│
├── backend/
│   ├── constraint_verifier/
│   │   ├── constraints.json               # ◀ SSOT for all ECE program rules
│   │   ├── constraint_schema.py           # Normalises constraints.json → flat dict
│   │   ├── constraint_verifier.py         # Rule engine (18 named checks)
│   │   └── test_constraint_verifier.py
│   ├── profile_generator/
│   │   ├── constraint_policy.py           # Typed dataclass bridge (JSON → solver)
│   │   ├── course_pool_builder.py         # Builds eligible course pool
│   │   ├── profile_course_loader.py       # Loads Course objects from the DB
│   │   ├── profile_generator.py           # Orchestrator + custom exceptions
│   │   ├── solver_cp_sat.py               # OR-Tools CP-SAT model + feedback constraints
│   │   ├── test_profile_generator.py
│   │   └── test_feedback_constraints.py   # Unit tests for feedback (LOCK/EXCLUDE/LIKE/DISLIKE)
│   ├── ranking_engine/
│   │   └── rag_model.py                   # RAG: embeddings (code+name+desc) + GPT-4 reranking
│   ├── data_bridge/                       # DB adapter layer (SQLite / in-memory)
│   │   ├── interfaces.py                  # CatalogBridge ABC
│   │   ├── models.py                      # RagDocument, CourseSearchRow, etc.
│   │   └── adapters/
│   │       ├── sqlite_adapter.py
│   │       └── in_memory_adapter.py
│   ├── data_pipeline/                     # DB init, migration, scraper CLI
│   └── types/                             # Course, CEABAttributes, constants
│
├── data/
│   ├── magellan.db                        # Canonical SQLite database
│   ├── course_codes/                      # Course-code source CSVs
│   ├── term/                              # Offering term source CSVs
│   ├── technical_classification/          # Area/kernel source CSVs
│   ├── ceab/                              # CEAB attribute source CSVs
│   └── excluded_course_codes.csv
│
├── frontend/                              # SvelteKit web interface
│   └── src/
│       ├── routes/
│       │   └── generate/
│       │       └── +page.svelte           # Main profile page + feedback loop UI
│       └── lib/
│           ├── api/
│           │   └── profile.ts             # generateProfile() + regenerateProfile()
│           ├── types/
│           │   ├── profile.ts             # ProfileResponse, RegenerateProfileResponse, etc.
│           │   └── feedback.ts            # FeedbackState, FeedbackRecord, HistoryEntry, etc.
│           └── components/
│               ├── SlotEditor.svelte      # Floating gear-icon popup for per-slot feedback
│               └── CourseDetailsModal.svelte
│
└── integration_test/
    ├── test_full_flow.py                  # End-to-end tests (initial generation)
    └── test_feedback_flow.py              # End-to-end tests (feedback loop, no LLM)
```

---

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+ and npm
- OpenAI API key

### 1. Environment

```bash
cd MagellanAI
echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
```

### 2. Backend

**Recommended - startup script:**
```bash
./start_backend.sh
```

**Manual:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements_api.txt

# Initialise DB (skip if magellan.db is already present and up to date)
python3 -m backend.data_pipeline.cli init-db
python3 -m backend.data_pipeline.cli migrate-from-folders --data-dir data
python3 -m backend.data_pipeline.cli scrape-missing-descriptions

python api_server.py
```

The backend starts at **`http://localhost:8000`**. A healthy start prints:
```
Starting MagellanAI API Server
✓ Data loaded successfully
INFO:     Uvicorn running on http://0.0.0.0:8000
```

> **First run after a code change to `rag_model.py`**: The `.rag_cache/` directory will be rebuilt automatically (fingerprint mismatch). This takes 30–90 seconds and only happens once.

### 3. Frontend (new terminal)

**Recommended - startup script:**
```bash
./start_frontend.sh
```

**Manual:**
```bash
cd frontend
npm install
npm run dev
```

The frontend opens at **`http://localhost:5173`**.

### 4. Generate and refine a profile

1. Open the app and describe your interests — e.g. *"I'm interested in machine learning, AI, and distributed systems."* You can also mention specific course codes directly, e.g. *"I want ECE421H1 in my profile."*
2. Select whether you took **ECE295H1** or **ECE297H1** in Year 2.
3. Click **Generate My Course Profile**.
4. Browse the generated semester plan, requirement breakdown, and CEAB summary.
5. Click the **⚙ gear icon** on any course slot to apply feedback (LOCK / EXCLUDE / LIKE / DISLIKE).
6. Click **"Regenerate with Feedback"** to produce a revised profile respecting your constraints. The Feedback Memory Panel below the grid shows all active feedback; individual entries can be removed with ✕ or all cleared at once.
7. Use the **"View iteration"** dropdown to browse past iterations (read-only).
8. Click **"Generate Fresh"** to start over with a completely new profile and empty feedback.

---

## Database Management

`magellan.db` is the canonical SQLite database. Rebuild or update it with the CLI:

```bash
# Full rebuild from source CSVs
python3 -m backend.data_pipeline.cli init-db
python3 -m backend.data_pipeline.cli migrate-from-folders --data-dir data

# Validate integrity
python3 -m backend.data_pipeline.cli validate

# Add or update a single course offering
python3 -m backend.data_pipeline.cli upsert-course \
  --course-code ECE999H1 \
  --term F \
  --course-type technical \
  --area 3 \
  --kernel 0 \
  --technical-elective 1 \
  --free-elective 1 \
  --math 0 --ns 0 --cs 0 --es 24 --ed 12
```

`upsert-course` behaviour:
- Insert-first: if `(course_code, term)` already exists, the CLI reports it and makes no change.
- For new offerings the CLI scrapes name and description from the UofT calendar; aborts on failure.
- Pass `--allow-update` only when explicitly overwriting an existing offering.

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check + loaded course count |
| `GET` | `/constraints` | ECE program constraint values from the SSOT |
| `GET` | `/year12-courses` | Year 1/2 course list for a given `year12_choice` |
| `GET` | `/courses` | Searchable/filterable course catalogue |
| `POST` | `/generate-profile` | Generate a personalised semester plan (RAG + CP-SAT) |
| `POST` | `/regenerate-profile` | Regenerate with feedback constraints (CP-SAT only, no LLM) |

---

### `POST /generate-profile`

```json
{
  "interests": "machine learning and AI",
  "num_recommendations": 15,
  "year12_choice": "ECE297H1"
}
```

Returns a `ProfileResponse`. The `preferences_used` and `preferences_skipped` fields indicate which ranked courses ended up in the profile.

---

### `POST /regenerate-profile`

Reruns the CP-SAT solver using a previously obtained preference list and a set of feedback constraints. The RAG model is **not called** — pass the original `preferences_used + preferences_skipped` from the first generation as `preferences`.

**Request body (`RegenerateProfileRequest`):**
```json
{
  "year12_choice": "ECE297H1",
  "preferences": ["ECE421H1", "ECE444H1", "..."],
  "feedback": {
    "locked":   ["ECE421H1"],
    "excluded":  ["ECE302H1"],
    "liked":     ["ECE454H1"],
    "disliked":  ["ECE472H1"]
  }
}
```

**Response (`RegenerateProfileResponse`)** — same fields as `ProfileResponse`, plus:

| Field | Type | Description |
|---|---|---|
| `success` | `bool` | `false` if solver timed out or feedback is infeasible |
| `timed_out` | `bool` | Solver exceeded 15-second limit |
| `feedback_infeasible` | `bool` | Constraints are mutually contradictory |
| `error` | `string \| null` | Human-readable error message when `success=false` |
| `feedback_result` | `FeedbackHonorReport \| null` | Per-course outcome for LIKE/DISLIKE feedback |

**`FeedbackHonorReport`:**
```json
{
  "liked_honored":    ["ECE454H1"],
  "liked_skipped":    [],
  "disliked_honored": ["ECE302H1"],
  "disliked_forced":  ["ECE472H1"]
}
```

**Validation errors returned before solving** (HTTP 400 / `success: false`):
- Same course appears in both `locked` and `excluded`
- A required course (e.g. ECE472H1) appears in `excluded`
- All capstone codes appear in `excluded`

**Rate limit:** Shares the same bucket as `/generate-profile` — 8 requests per 60 seconds per IP.

**`GET /constraints`** serves all numeric thresholds and flags from `constraints.json` so the frontend never hardcodes ECE program values.

---

## Testing

```bash
# Unit tests
.venv/bin/python -m pytest backend/constraint_verifier/test_constraint_verifier.py -v
.venv/bin/python -m pytest backend/profile_generator/test_profile_generator.py -v

# Feedback loop unit tests (no LLM, no network)
.venv/bin/python -m pytest backend/profile_generator/test_feedback_constraints.py -v

# All backend tests at once
.venv/bin/python -m pytest backend/ -v

# Integration tests (requires a live DB; RAG is mocked)
.venv/bin/python -m pytest integration_test/test_full_flow.py -v
.venv/bin/python -m pytest integration_test/test_feedback_flow.py -v

# Full suite
.venv/bin/python -m pytest -v

# Quick API smoke tests
curl http://localhost:8000/health
curl -X POST http://localhost:8000/generate-profile \
  -H "Content-Type: application/json" \
  -d '{"interests": "machine learning and AI", "num_recommendations": 15}'
```

Current baseline: **88 tests, 0 failures** (1 skipped — requires specific hardware state).

### Test coverage overview

| File | What it covers |
|---|---|
| `test_constraint_verifier.py` | All 18 named ECE rule checks |
| `test_profile_generator.py` | Full generation pipeline, edge cases |
| `test_feedback_constraints.py` | LOCK / EXCLUDE / LIKE / DISLIKE solver constraints; honor report; timeouts |
| `test_full_flow.py` | End-to-end: DB → RAG (mocked) → CP-SAT → verifier → response shape |
| `test_feedback_flow.py` | End-to-end feedback loop: lock/exclude/like/dislike/combined; honor report; capstone placement; timeout |
| `test_catalog_bridge.py` | Data bridge adapter correctness |

---

## ECE Program Constraints - Single Source of Truth

### Where rules live

```
backend/constraint_verifier/constraints.json   ← THE SINGLE SOURCE OF TRUTH
```

Every numeric threshold, boolean flag, and enumerated list that governs constraint checking, profile generation, or UI display is defined in this file. **Never hardcode ECE program values anywhere else.** When a program rule changes, update `constraints.json` first — all downstream modules read it automatically via the pipeline:

```
constraints.json
  └─▶ constraint_schema.py      (normalises to a flat dict)
        └─▶ constraint_policy.py     (typed frozen dataclass for the solver)
              ├─▶ solver_cp_sat.py       (CP-SAT hard constraints)
              └─▶ constraint_verifier.py (18 named rule checks)
```

The `GET /constraints` endpoint serves the same values to the frontend, so the UI also stays in sync without any hardcoding.

### Constraint quick-reference

| ECE Rule | `constraints.json` path |
|---|---|
| Total credits = 10.0 | `hard_requirements.total_num_credits` |
| ECE472H1 required | `hard_requirements.ece472_required` |
| Capstone required (exactly 1) | `hard_requirements.capstone_required` |
| Valid capstone codes | `capstone.codes` |
| Capstone must be in Year 4 only | `capstone.must_be_in_year4`, `capstone.year4_semester_indices` |
| Breadth: 4 areas, 1 kernel each | `hard_requirements.breadth.*` |
| Depth: 2 areas, 3 courses each | `hard_requirements.depth.*` |
| Math/Science: ≥ 1 from area 7 | `hard_requirements.math_sci.*` |
| Technical electives: ≥ 3 | `hard_requirements.technical_electives.*` |
| Complementary studies: ≥ 4 (≥ 2 HSS) | `hard_requirements.complementary.*` |
| Free elective: ≥ 1 | `hard_requirements.free_elective.*` |
| Year-3 technical: ≥ 7 (or ≥ 6 if ECE472 in Y3) | `hard_requirements.year3_technical.*` |
| No H3/H5 courses | `hard_requirements.exclude_h3_h5` |
| CSC3\*/CSC4\* ≤ 1.5 credits | `hard_requirements.max_csc34_credits` |
| No course code repeated | `hard_requirements.no_repetition` |
| Slots per semester | `profile_shape.slots_per_term` |
| Semester layout (3F/3S/4F/4S) | `profile_shape.terms` |
| Capstone semester indices | `profile_shape.capstone_semester_indices` |
| No non-capstone Y-term courses | `profile_shape.allow_non_capstone_y` |
| Year 1/2 CEAB baseline included | `assumptions.include_year12_ceab_baseline` |
| ECE295H1 or ECE297H1 default | `assumptions.year12_default_choice` |
| CEAB AU targets (8 categories) | `ceab_requirements.targets.*` |
| CEAB pre-obtained credits | `ceab_requirements.preobtained.*` |

### No-overlap rule

Each course code satisfies **exactly one** requirement category. ECE472H1 and all capstone codes are reserved for the *Required* category and cannot count towards breadth, depth, math/sci, technical elective, complementary, or free elective requirements.

### Constraint verifier rule registry

The verifier runs 18 named checks on every profile:

| Rule name | What it checks |
|---|---|
| Total Credits Requirement | Sum of credits == 10.0 |
| Required Course Set | ≥ 1 non-capstone required course present |
| ECE472 Required | ECE472H1 in profile |
| Capstone Required | Exactly 1 capstone course |
| **Capstone Placement (Year 4 Only)** | Capstone not in 3F or 3S |
| Breadth Requirement | 4 areas with ≥ 1 kernel each (required courses excluded) |
| Depth Requirement | 2 areas with ≥ 3 courses and ≥ 1 kernel each (required courses excluded) |
| Math/Science (Area 7) Requirement | ≥ 1 area-7 course |
| Term Validity | No non-capstone Y-term courses |
| No H3/H5 Courses | No H3/H5 suffix course codes |
| CSC3\*/CSC4\* Credit Cap | ≤ 1.5 credits of 300/400-level CSC |
| Complementary Studies Requirement | ≥ 4 complementary, ≥ 2 HSS |
| Year 3 Technical Course Requirement | ≥ 7 technical in 3F+3S (or ≥ 6 if ECE472 in Y3) |
| Technical Elective Requirement | ≥ 3 technical electives beyond breadth/depth/math-sci |
| Free Elective Requirement | ≥ 1 free elective |
| No Repetition Requirement | No repeated course codes (capstone double-slot is exempt) |
| Semester Count (Exactly 4) | Profile has exactly 4 semesters |
| Course Load (== 5 per semester) | Each semester has exactly `slots_per_term` courses |

---

## Architecture Notes

### Profile generation

- **Preferences are soft**: The CP-SAT solver maximises a weighted preference score but always prioritises feasibility. A preference may be skipped if it conflicts with hard constraints.
- **CP-SAT timeouts**: Initial generation uses an **8-second** solver timeout. Regeneration with feedback uses **15 seconds** because the additional constraints can make the search harder.
- **ECE295H1 vs ECE297H1**: Exactly one is taken in Year 2. The chosen course's CEAB attributes form a baseline that is subtracted from the CEAB targets before solving Year 3/4.
- **Capstone double-slot**: A Y-term capstone (e.g. ECE496Y1) appears in both 4F and 4S but counts as one course code, 1.0 credit, and its CEAB attributes are summed once.
- **`exclude_h3_h5`**: Courses with an H3 or H5 suffix are excluded from the pool. This flag is read from `constraints.json` — flipping it to `false` will allow those courses.

### Feedback loop implementation

- **LOCK / EXCLUDE are hard constraints**: Implemented as `model.Add(y[code] == 1)` and `model.Add(y[code] == 0)` on the binary course-selection variable. An unresolvable LOCK (course not in pool) raises `SolverInfeasibleError` immediately without invoking the solver.
- **LIKE is a soft boost (+100)**: Added directly to the CP-SAT maximisation objective alongside the rank-based preference weights. A liked course that genuinely fits the constraints will reliably be selected; one that conflicts with hard constraints will be skipped and reported in `liked_skipped`.
- **DISLIKE is a soft penalty (−100)**: Same objective, negative sign. This is "Option A" — the penalty is never large enough to cause infeasibility. A required course that is disliked will still appear in the profile and be reported in `disliked_forced`. This means users cannot accidentally break constraint satisfaction by disliking required courses.
- **Custom exceptions**: `SolverTimeoutError` and `SolverInfeasibleError` are defined in `profile_generator.py` and raised by the orchestrator; `api_server.py` catches them to return structured `RegenerateProfileResponse` with appropriate flags.
- **Feedback is course-code keyed**: Since capstone occupies two grid slots with the same code, both slots are automatically synchronised — no special frontend logic is needed.
- **Feedback persistence**: Session-only (in-memory, lost on refresh). The `FeedbackRecord` type (`Record<string, FeedbackState>`) and `HistoryEntry` interface are designed so a future backend persistence layer can be added without restructuring the frontend state.
- **Carry-forward**: After each regeneration the submitted feedback is preserved as the starting state for the next iteration, not cleared. Users see which constraints are still active and can modify or remove them incrementally.
- **Course-name cache**: The frontend maintains a `courseNameCache` (course_code → name) that accumulates from every profile loaded in the session. This allows the Feedback Memory Panel to resolve course names for excluded courses that no longer appear in the current profile's grid.

### Ranking engine

- **Embedding content (v2)**: Each course's embedded text is `"COURSE_CODE. Course Name. Description"`. Prepending the code ensures that if a user explicitly types a course code in their interests prompt, the cosine similarity phase (Phase 1) picks it up directly, not just semantically.
- **Year 1/2 courses excluded from RAG index**: Courses flagged `is_year1_year2 = true` in the database are excluded from both the embedding index and the LLM candidate list. The `get_rag_documents` bridge method accepts `exclude_year1_year2=True` to enforce this. Year 1/2 courses are pre-requisites that students have already completed; recommending them as Year 3/4 choices would be incorrect.
- **RAG cache**: Sentence-transformer embeddings are cached in `.rag_cache/`. The cache fingerprint includes `_EMBEDDING_SCHEMA_VERSION` (currently `"v2"`). Whenever the embedding content changes (new fields in `prepare_texts`, new filters), bump this constant and the cache will be rebuilt automatically on the next server start. Do not delete `.rag_cache/` manually — it is rebuilt automatically when stale.
- **LLM phase (Phase 2)**: The GPT-4 reranking call receives `"COURSE_CODE\tCourseName. Description"` per candidate. The system prompt instructs the model to treat an explicitly mentioned course code as a strong signal.
- **RAG is not invoked during regeneration**: The `/regenerate-profile` endpoint accepts the original `preferences` list directly and passes it straight to the CP-SAT solver. This makes full end-to-end feedback-loop tests possible without an OpenAI key.

### Data bridge

- `CatalogBridge` (abstract base class in `interfaces.py`) defines the contract between the ranking engine, profile generator, and the database. There are two implementations: `SQLiteCatalogAdapter` (production) and `InMemoryCatalogAdapter` (tests). Any new query that touches course data should go through this interface to stay adapter-agnostic.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError` | `pip install -r requirements.txt && pip install -r requirements_api.txt` |
| `OPENAI_API_KEY not set` | `export OPENAI_API_KEY="sk-..."` or add it to `.env` |
| `Data missing / DB not initialised` | Run `init-db` + `migrate-from-folders` + `scrape-missing-descriptions` (see Quick Start) |
| `Failed to generate profile` (frontend) | Check backend is on port 8000; inspect browser console; verify `OPENAI_API_KEY` |
| Port already in use | `npx kill-port 5173` (frontend) or `npx kill-port 8000` (backend) |
| Initial generation times out | The CP-SAT solver has an 8-second limit; extremely rare with the full course catalogue |
| Regeneration times out (⏱ banner) | Solver hit the 15-second limit. Try fewer or less restrictive LOCK/EXCLUDE constraints |
| "No valid profile exists with these constraints" | Conflicting feedback (e.g. LOCK + EXCLUDE same course, or all capstones excluded). Relax constraints and retry |
| Slow backend start after code changes | `.rag_cache/` is being rebuilt (embedding schema changed). Wait 30–90 s for the index to rebuild |
| Stale `.rag_cache/` producing unexpected rankings | Delete `.rag_cache/` — it will be rebuilt on next start |
| DISLIKE has no visible effect | DISLIKE is a soft −100 penalty. Required courses (e.g. ECE472H1) will still appear because the hard constraint overrides the penalty. Use EXCLUDE to hard-block a non-required course |
| Rate limit error (HTTP 429) | Both `/generate-profile` and `/regenerate-profile` share 8 req / 60 s per IP. Wait and retry |

---

## README Maintenance

This README is the primary reference for understanding MagellanAI's architecture, features, and design decisions. When making changes to the codebase, update this file for any of the following:

- **New API endpoints** — add to the API Reference table and document request/response shapes
- **New or changed solver constraints** — update the CP-SAT behaviour notes in Architecture Notes
- **New or changed user-facing features** — update How It Works and/or add a dedicated feature section (as done for the Interactive Feedback Loop)
- **Changes to the SSOT pipeline** (`constraints.json` → solver/verifier flow) — update the SSOT section
- **Changes to the RAG/embedding pipeline** — update the ranking engine notes (especially if `_EMBEDDING_SCHEMA_VERSION` is bumped)
- **New test files or significant test coverage changes** — update the Testing section and the test coverage table
- **New dependencies or infrastructure changes** — update Quick Start and/or Architecture Notes
- **Changes to the data bridge interface** (`interfaces.py`) — update Architecture Notes and any affected API docs

Keep descriptions concise but precise. Future maintainers should be able to understand the *why* behind each architectural decision, not just the *what*.

---

## Contributors

Snehal Sobti, Ishika Mittal, Hamza Mohammed, Krishna Advait Sripada

*Undergraduate Capstone Project - University of Toronto*
