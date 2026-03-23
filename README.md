# MagellanAI

An intelligent course-planning assistant for upper-year Electrical and Computer Engineering (ECE) students at the University of Toronto. MagellanAI accepts a student's interests in plain English, then automatically generates a complete, valid, and personalized 10-credit Year 3/4 course profile that satisfies every ECE graduation requirement.

---

## Table of Contents

1. [How It Works](#how-it-works)
2. [Project Structure](#project-structure)
3. [Quick Start](#quick-start)
4. [Database Management](#database-management)
5. [API Reference](#api-reference)
6. [Testing](#testing)
7. [ECE Program Constraints - Single Source of Truth](#ece-program-constraints--single-source-of-truth)
8. [Architecture Notes](#architecture-notes)
9. [Troubleshooting](#troubleshooting)
10. [Contributors](#contributors)

---

## How It Works

```
User interests (text)
      ↓
POST /generate-profile
      ↓
RAG Model  ──  semantic search (sentence-transformers) + GPT-4 reranking
      │         → ranked list of relevant course codes
      ↓
Profile Generator (CP-SAT solver)
      │         → feasible 10-credit semester plan satisfying all constraints
      ↓
Constraint Verifier  ──  double-checks every ECE rule
      ↓
Response  ──  semester plan, requirement buckets, CEAB summary, stats
```

**Key properties of the generated profile:**
- Exactly 20 semester slots across 3F / 3S / 4F / 4S (5 per semester)
- 19 unique course codes → 10.0 credits (18 × 0.5 H-courses + 1 × 1.0 Y capstone)
- All ECE breadth, depth, CEAB, complementary, and elective rules enforced as hard constraints
- Student preferences are a soft objective - maximised within the feasible region

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
│   │   ├── profile_generator.py           # Orchestrator
│   │   ├── solver_cp_sat.py               # OR-Tools CP-SAT model
│   │   └── test_profile_generator.py
│   ├── ranking_engine/
│   │   └── rag_model.py                   # RAG: embeddings + GPT-4 reranking
│   ├── data_bridge/                       # DB adapter layer (SQLite / in-memory)
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
│       ├── routes/                        # Page components
│       └── lib/                           # API client, types, shared components
│
└── integration_test/
    └── test_full_flow.py                  # End-to-end tests
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

### 4. Generate a profile

1. Open the app and describe your interests - e.g. *"I'm interested in machine learning, AI, and distributed systems."*
2. Select whether you took **ECE295H1** or **ECE297H1** in Year 2.
3. Click **Generate My Course Profile**.
4. Browse the generated semester plan, requirement breakdown, and CEAB summary.

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
| `POST` | `/generate-profile` | Generate a personalised semester plan |

**`POST /generate-profile` body:**
```json
{
  "interests": "machine learning and AI",
  "num_recommendations": 15,
  "year12_choice": "ECE297H1"
}
```

**`GET /constraints`** - serves all numeric thresholds and flags from `constraints.json` so the frontend never hardcodes ECE program values.

---

## Testing

```bash
# Unit tests
.venv/bin/python -m pytest backend/constraint_verifier/test_constraint_verifier.py -v
.venv/bin/python -m pytest backend/profile_generator/test_profile_generator.py -v

# All at once
.venv/bin/python -m pytest backend/ -v

# Integration tests (requires a live DB)
.venv/bin/python -m pytest integration_test/test_full_flow.py -v

# Quick API smoke tests
curl http://localhost:8000/health
curl -X POST http://localhost:8000/generate-profile \
  -H "Content-Type: application/json" \
  -d '{"interests": "machine learning and AI", "num_recommendations": 15}'
```

Current baseline: **45 unit/integration tests, 0 failures**.

---

## ECE Program Constraints - Single Source of Truth

### Where rules live

```
backend/constraint_verifier/constraints.json   ← THE SINGLE SOURCE OF TRUTH
```

Every numeric threshold, boolean flag, and enumerated list that governs constraint checking, profile generation, or UI display is defined in this file. **Never hardcode ECE program values anywhere else.** When a program rule changes, update `constraints.json` first - all downstream modules read it automatically via the pipeline:

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

- **RAG cache**: Sentence-transformer embeddings are cached in `.rag_cache/`. The first run is slower while the cache is built.
- **Preferences are soft**: The CP-SAT solver maximises a weighted preference score but always prioritises feasibility. A preference may be skipped if it conflicts with hard constraints.
- **ECE295H1 vs ECE297H1**: Exactly one is taken in Year 2. The chosen course's CEAB attributes form a baseline that is subtracted from the CEAB targets before solving Year 3/4.
- **Capstone double-slot**: A Y-term capstone (e.g. ECE496Y1) appears in both 4F and 4S but counts as one course code, 1.0 credit, and its CEAB attributes are summed once.
- **`exclude_h3_h5`**: Courses with an H3 or H5 suffix are excluded from the pool. This flag is read from `constraints.json` - flipping it to `false` will allow those courses.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError` | `pip install -r requirements.txt && pip install -r requirements_api.txt` |
| `OPENAI_API_KEY not set` | `export OPENAI_API_KEY="sk-..."` or add it to `.env` |
| `Data missing / DB not initialised` | Run `init-db` + `migrate-from-folders` + `scrape-missing-descriptions` (see Quick Start) |
| `Failed to generate profile` (frontend) | Check backend is on port 8000; inspect browser console; verify `OPENAI_API_KEY` |
| Port already in use | `npx kill-port 5173` (frontend) or `npx kill-port 8000` (backend) |
| Profile generation times out | The CP-SAT solver has an 8-second limit; this is rare with the full course catalogue |

---

## Contributors

Snehal Sobti, Ishika Mittal, Hamza Mohammed, Krishna Advait Sripada

*Undergraduate Capstone Project - University of Toronto*
