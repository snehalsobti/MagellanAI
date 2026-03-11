# MagellanAI Redesign Review Guide

This document summarizes all changes since the last commit and provides a recommended code review order.

## Recommended Review Order

Review in this order to understand the architecture top-down:

1. `backend/constraint_verifier/constraints.json`
2. `backend/constraint_verifier/constraint_schema.py`
3. `backend/profile_generator/constraint_policy.py`
4. `backend/types/ceab_baseline.py`
5. `backend/profile_generator/course_pool_builder.py`
6. `backend/profile_generator/solver_cp_sat.py`
7. `backend/profile_generator/profile_generator.py`
8. `backend/constraint_verifier/constraint_verifier.py`
9. `api_server.py`
10. `backend/profile_generator/profile_course_loader.py`
11. `backend/types/ceab_attributes.py`
12. `backend/types/course.py`
13. Data-layer updates:
    - `backend/data_pipeline/schema.py`
    - `backend/data_pipeline/migrate_from_folders.py`
    - `backend/data_bridge/models.py`
    - `backend/data_bridge/interfaces.py`
    - `backend/data_bridge/adapters/sqlite_adapter.py`
    - `backend/data_bridge/adapters/in_memory_adapter.py`
    - `backend/data_pipeline/cli.py`
14. Test updates:
    - `backend/profile_generator/test_profile_generator.py`
    - `backend/constraint_verifier/test_constraint_verifier.py`
    - `integration_test/test_full_flow.py`
15. `requirements.txt`
16. `data/magellan.db` (generated artifact; review only if DB snapshot is intentionally versioned)

---

## Architecture After Redesign

### Generation path (runtime)

`API -> ProfileGenerator -> GlobalCpSatProfileSolver -> ConstraintVerifier.evaluate() -> response diagnostics`

- **Primary solver is CP-SAT**.
- Profile generation path is now CP-SAT-only (no compare/heuristic strategy branches).
- Generation returns structured diagnostics:
  - engine used
  - solver runtime
  - preference hit count / weighted score
  - verifier diagnostics

### Constraints model

- `constraints.json` is now **structured** (`profile_shape`, `assumptions`, `hard_requirements`, `ceab_requirements`).
- `constraint_schema.normalize_constraints()` now strictly validates and normalizes the structured schema only.
- CEAB is enabled in config (`ceab_requirements.enabled = true`).

### CEAB handling

- CEAB values are now float-preserving end-to-end (no truncation).
- Year1/Year2 CEAB baseline is computed from `data/ceab/year1_year2.csv` with configurable `ECE295H1` vs `ECE297H1` choice.
- CP-SAT and verifier both incorporate baseline consistently for CEAB checks.

### Data model additions

- Course metadata now includes:
  - `is_year1_year2`
  - `is_required`
  - `is_excluded` passthrough
- `H3/H5` handling is centralized as exclusion behavior in migration and generation eligibility.

---

## Per-File Change Summary (since last commit)

## 1) Constraints and schema normalization

- **`backend/constraint_verifier/constraints.json`**
  - Migrated from flat keys to structured schema.
  - Enabled CEAB checks by default.
  - Encodes assumptions, hard constraints, and CEAB targets in nested blocks.

- **`backend/constraint_verifier/constraint_schema.py`** *(new)*
  - Added schema normalizer for the structured constraints format used by verifier/policy.
  - Produces normalized keys used by verifier and policy parser.

## 2) Policy and CEAB baseline

- **`backend/profile_generator/constraint_policy.py`** *(new in redesign, then expanded)*
  - Centralized loading of generation policy from normalized constraints.
  - Added CEAB-net targets and baseline-derived values.
  - Supports per-request `year12_choice`.

- **`backend/types/ceab_baseline.py`** *(new)*
  - Computes Year1/2 CEAB baseline from CSV.
  - Handles one-of choice (`ECE295H1` or `ECE297H1`).

## 3) Solver and generation core

- **`backend/profile_generator/course_pool_builder.py`** *(new)*
  - Canonical course eligibility and pool construction.
  - Metadata-driven required/capstone logic.
  - Exclusion rules (`is_excluded`, H3/H5).

- **`backend/profile_generator/solver_cp_sat.py`** *(new and iterated)*
  - CP-SAT term selector and global profile solver.
  - Semester-level assignment variables for `3F/3S/4F/4S`.
  - Hard constraints encoded in-model:
    - required/capstone
    - breadth/depth/math-sci
    - complementary/HSS
    - technical electives / free elective
    - year-3 technical conditional rule
    - CSC3*/CSC4* cap
    - CEAB lower bounds (with baseline compensation)
  - Objective uses ranked preference weighting.

- **`backend/profile_generator/profile_generator.py`**
  - Cleaned to CP-SAT-first orchestration.
  - Removed large legacy heuristic construction path and compare-mode branching.
  - Normalizes preferences, invokes solver, computes metadata/diagnostics, verifies with `ConstraintVerifier.evaluate()`.
  - Emits a single generation engine label: `cp_sat`.

## 4) Verifier refactor

- **`backend/constraint_verifier/constraint_verifier.py`**
  - Uses normalized constraints.
  - Added rule-registry style evaluation (`RuleCheck`, `evaluate()`).
  - `verify()` now delegates to `evaluate()` and prints failures.
  - CEAB baseline loaded consistently (supports year12 override).
  - Added/expanded checks for term validity, complementary, technical/free elective, year3 technical, CSC cap, etc.

## 5) API and response diagnostics

- **`api_server.py`**
  - Default solver strategy switched to CP-SAT.
  - Request supports `year12_choice`.
  - Response includes diagnostics fields:
    - `generation_engine`
    - `solver_runtime_ms`
    - `preference_hit_count`
    - `preference_weighted_score`
    - `constraint_diagnostics`

## 6) Course loading/types precision and metadata

- **`backend/profile_generator/profile_course_loader.py`**
  - Profile loading is bridge-wide candidate loading (not technical-only hardcoding).
  - CEAB values preserved as floats.
  - Includes metadata flags in `Course` objects.

- **`backend/types/ceab_attributes.py`**
  - Changed CEAB storage from int-style to float-style.

- **`backend/types/course.py`**
  - Expanded model with metadata fields used by solver/verifier:
    - `course_type`
    - `non_technical_type`
    - `is_year1_year2`
    - `is_required`
    - `is_excluded`

## 7) Data pipeline and bridge

- **`backend/data_pipeline/schema.py`**
  - Added classification fields for `is_year1_year2`, `is_required`.

- **`backend/data_pipeline/migrate_from_folders.py`**
  - Tags year1/year2 and required from source CSVs.
  - Auto-excludes H3/H5 offerings.

- **`backend/data_bridge/models.py`**
  - Added new metadata fields in dataclasses.

- **`backend/data_bridge/interfaces.py`**
  - Added profile-oriented query methods (`get_profile_candidate_courses`, `get_courses_by_codes`).

- **`backend/data_bridge/adapters/sqlite_adapter.py`**
  - Wired new metadata columns in reads/writes and filters.
  - Added implementations for new profile query methods.

- **`backend/data_bridge/adapters/in_memory_adapter.py`**
  - Parallel support for new metadata and query methods.

- **`backend/data_pipeline/cli.py`**
  - Added CLI support for new metadata flags in upsert flow.

## 8) Tests

- **`backend/profile_generator/test_profile_generator.py`**
  - Added CP-SAT path assertions and diagnostics field checks.
  - Added complementary/free requirement test.

- **`backend/constraint_verifier/test_constraint_verifier.py`**
  - Updated CEAB and math/sci expectations for redesigned verifier behavior.
  - Added baseline toggles in synthetic CEAB tests.

- **`integration_test/test_full_flow.py`**
  - Added deterministic CP-SAT integration test with diagnostics assertions.
  - Added diagnostics-shape checks.
  - Networked RAG test made explicit opt-in (`ALLOW_NETWORK_RAG_TEST=1`).

## 9) Dependencies / artifacts

- **`requirements.txt`**
  - Added `ortools` for CP-SAT.

- **`data/magellan.db`**
  - Rebuilt/migrated schema and metadata to reflect new pipeline changes.

---

## Suggested Final Review Pass (quick)

After code review, run:

1. `./.venv/bin/python -m unittest backend/profile_generator/test_profile_generator.py`
2. `./.venv/bin/python -m unittest backend/constraint_verifier/test_constraint_verifier.py`
3. `./.venv/bin/python -m unittest backend/data_bridge/test_catalog_bridge.py`
4. `./.venv/bin/python -m unittest integration_test/test_full_flow.py`

Note: the networked RAG integration test is opt-in and only runs when both
`OPENAI_API_KEY` and `ALLOW_NETWORK_RAG_TEST=1` are set.

