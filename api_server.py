# api_server.py
# FastAPI server that connects frontend to backend pipeline

from collections import defaultdict, deque
import gc
import json
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pathlib import Path
import os
import sys
import time

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from backend.ranking_engine.rag_model import rag_model
from backend.data_bridge.factory import get_catalog_bridge
from backend.profile_generator.profile_generator import ProfileGenerator, SolverTimeoutError, SolverInfeasibleError
from backend.profile_generator.profile_course_loader import ProfileCourseLoader
from backend.constraint_verifier.constraint_verifier import ConstraintVerifier
from backend.constraint_verifier.constraint_schema import normalize_constraints
from backend.course_query_system.basic_query import load_course_details_index

app = FastAPI(title="MagellanAI API")

# Enable CORS for frontend (env-configurable, not wildcard)
allowed_origins_env = os.getenv("MAGELLAN_ALLOWED_ORIGINS", "")
allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]
if not allowed_origins:
    allowed_origins = ["http://localhost:3000", "http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    catalog_bridge = get_catalog_bridge()
    issues = catalog_bridge.validate_catalog()
    if issues:
        print("Catalog validation issues detected:")
        for issue in issues:
            print(f" - {issue}")
    profile_courses = ProfileCourseLoader.load_profile_courses_from_bridge(catalog_bridge)
    if not profile_courses:
        print("Warning: no profile courses found in catalog. Run data pipeline migration/upserts first.")
    course_lookup = load_course_details_index(bridge=catalog_bridge)
    profile_generator = ProfileGenerator(profile_courses)
    # Pre-compute required non-capstone codes for feedback validation (SSOT: is_required flag)
    _required_noncap_codes: frozenset[str] = frozenset(
        c.course_code for c in profile_courses
        if bool(getattr(c, "is_required", False)) and c.term != "Y"
    )
    _capstone_codes_pool: frozenset[str] = frozenset(
        c.course_code for c in profile_courses
        if bool(getattr(c, "is_required", False)) and c.term == "Y"
    )
    print("[ProfileGen] Strategy: cp_sat")
    print("✓ Data loaded successfully")
except Exception as e:
    print(f"Error loading data: {e}")
    catalog_bridge = None
    profile_courses = []
    course_lookup = {}
    profile_generator = None
    _required_noncap_codes: frozenset[str] = frozenset()
    _capstone_codes_pool: frozenset[str] = frozenset()


class UserInterestRequest(BaseModel):
    interests: str = Field(..., min_length=1, max_length=2000)
    num_recommendations: int = Field(default=15, ge=1, le=30)
    year12_choice: str | None = None


class SemesterPlanRow(BaseModel):
    term: str  # "3F", "3S", "4F", "4S"
    course_codes: list[str]


class CourseInfo(BaseModel):
    course_code: str
    course_name: str
    course_description: str | None = None
    area: int
    term: str | None = None
    num_credits: float
    kernel_course: bool
    technical_elective: bool
    free_elective: bool = False
    course_type: str | None = None
    non_technical_type: str | None = None
    ceab_math: float | None = None
    ceab_ns: float | None = None
    ceab_cs: float | None = None
    ceab_es: float | None = None
    ceab_ed: float | None = None


class CourseSearchResponse(BaseModel):
    success: bool
    courses: list[CourseInfo]


class Year12CoursesResponse(BaseModel):
    success: bool
    year12_choice: str
    courses: list[str]


class ProfileResponse(BaseModel):
    success: bool
    courses: list[CourseInfo]
    semester_plan: list[SemesterPlanRow] = []
    total_credits: float
    kernel_areas_selected: list[int]
    depth_areas_selected: list[int]
    preferences_used: list[str]
    preferences_skipped: list[str]
    constraints_satisfied: bool
    generation_engine: str | None = None
    solver_runtime_ms: float | None = None
    preference_hit_count: int | None = None
    preference_weighted_score: int | None = None
    constraint_diagnostics: dict | None = None
    error: str = None


class ConstraintsDisplayResponse(BaseModel):
    """ECE program constraint values served from the SSOT for frontend display."""
    total_num_credits: float
    slots_per_term: int
    capstone_codes: list[str]
    min_breadth_areas: int
    min_depth_areas: int
    min_courses_per_depth_area: int
    min_math_sci_courses: int
    min_technical_elective_courses: int
    min_complementary_courses: int
    min_hss_in_complementary: int
    min_free_elective_courses: int
    max_csc34_credits: float
    year3_min_technical_courses: int
    year3_min_technical_courses_if_ece472: int
    year12_default_choice: str
    ceab_total_au: float
    ceab_cs: float
    ceab_math: float
    ceab_ns: float
    ceab_math_ns: float
    ceab_es: float
    ceab_ed: float
    ceab_es_ed: float


class FeedbackPayload(BaseModel):
    locked: list[str] = []
    excluded: list[str] = []
    liked: list[str] = []
    disliked: list[str] = []


class RegenerateProfileRequest(BaseModel):
    interests: str = Field(default="", max_length=2000)
    num_recommendations: int = Field(default=15, ge=1, le=30)
    year12_choice: str | None = None
    preferences: list[str] = Field(default_factory=list)
    feedback: FeedbackPayload = Field(default_factory=FeedbackPayload)


class FeedbackHonorReport(BaseModel):
    liked_honored: list[str] = []
    liked_skipped: list[str] = []
    # DISLIKE (soft penalty, Option A): honored = not placed, forced = still placed
    disliked_honored: list[str] = []
    disliked_forced: list[str] = []


class RegenerateProfileResponse(BaseModel):
    success: bool
    courses: list[CourseInfo] = []
    semester_plan: list[SemesterPlanRow] = []
    total_credits: float = 0.0
    kernel_areas_selected: list[int] = []
    depth_areas_selected: list[int] = []
    preferences_used: list[str] = []
    preferences_skipped: list[str] = []
    constraints_satisfied: bool = False
    generation_engine: str | None = None
    solver_runtime_ms: float | None = None
    preference_hit_count: int | None = None
    preference_weighted_score: int | None = None
    constraint_diagnostics: dict | None = None
    error: str | None = None
    feedback_result: FeedbackHonorReport | None = None
    timed_out: bool = False
    feedback_infeasible: bool = False


class InMemoryRateLimiter:
    def __init__(self, *, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> bool:
        now = time.monotonic()
        bucket = self._buckets[key]
        cutoff = now - self.window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= self.max_requests:
            return False
        bucket.append(now)
        return True


rate_limiter = InMemoryRateLimiter(max_requests=8, window_seconds=60)


def _extract_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _to_course_info(course, details=None) -> CourseInfo:
    name = "Name not available"
    description = None
    if details is not None:
        name = details.name or name
        description = details.description
    return CourseInfo(
        course_code=course.course_code,
        course_name=name,
        course_description=description,
        area=course.area if course.area else -1,
        term=getattr(course, "term", None),
        num_credits=getattr(course, "num_credits", 0.5),
        kernel_course=bool(getattr(course, "kernel_course", False)),
        technical_elective=bool(getattr(course, "technical_elective", False)),
        free_elective=bool(getattr(course, "free_elective", False)),
        course_type=getattr(course, "course_type", None),
        non_technical_type=getattr(course, "non_technical_type", None),
        ceab_math=float(getattr(getattr(course, "ceab", None), "mathematics", 0.0) or 0.0),
        ceab_ns=float(getattr(getattr(course, "ceab", None), "natural_science", 0.0) or 0.0),
        ceab_cs=float(getattr(getattr(course, "ceab", None), "complementary_studies", 0.0) or 0.0),
        ceab_es=float(getattr(getattr(course, "ceab", None), "engineering_science", 0.0) or 0.0),
        ceab_ed=float(getattr(getattr(course, "ceab", None), "engineering_design", 0.0) or 0.0),
    )


@app.get("/")
async def root():
    return {
        "message": "MagellanAI API",
        "status": "running",
        "endpoints": {
            "/generate-profile": "POST - Generate course profile from user interests"
        }
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "data_loaded": profile_generator is not None,
        "num_profile_courses": len(profile_courses) if profile_courses else 0,
    }


@app.get("/constraints", response_model=ConstraintsDisplayResponse)
async def get_constraints():
    """
    Serve the ECE program constraint display values from the SSOT
    (backend/constraint_verifier/constraints.json).
    Frontend pages use this to avoid hardcoding any program numbers.
    """
    _constraints_path = Path(__file__).resolve().parent / "backend" / "constraint_verifier" / "constraints.json"
    with open(_constraints_path, "r", encoding="utf-8") as _f:
        _raw = normalize_constraints(json.load(_f))
    return ConstraintsDisplayResponse(
        total_num_credits=_raw["total_num_credits"],
        slots_per_term=_raw["slots_per_term"],
        capstone_codes=_raw["capstone_codes"],
        min_breadth_areas=_raw["min_breadth_areas"],
        min_depth_areas=_raw["min_depth_areas"],
        min_courses_per_depth_area=_raw["min_courses_per_depth_area"],
        min_math_sci_courses=_raw["min_math_sci_courses"],
        min_technical_elective_courses=_raw["min_technical_elective_courses"],
        min_complementary_courses=_raw["min_complementary_courses"],
        min_hss_in_complementary=_raw["min_hss_in_complementary"],
        min_free_elective_courses=_raw["min_free_elective_courses"],
        max_csc34_credits=_raw["max_csc34_credits"],
        year3_min_technical_courses=_raw["year3_min_technical_courses"],
        year3_min_technical_courses_if_ece472=_raw["year3_min_technical_courses_if_ece472"],
        year12_default_choice=_raw["year12_default_choice"],
        ceab_total_au=_raw["ceab_total_au"],
        ceab_cs=_raw["ceab_cs"],
        ceab_math=_raw["ceab_math"],
        ceab_ns=_raw["ceab_ns"],
        ceab_math_ns=_raw["ceab_math_ns"],
        ceab_es=_raw["ceab_es"],
        ceab_ed=_raw["ceab_ed"],
        ceab_es_ed=_raw["ceab_es_ed"],
    )


@app.post("/generate-profile", response_model=ProfileResponse)
async def generate_profile(request: Request, payload: UserInterestRequest):
    """
    Main endpoint: Takes user interests, runs RAG → ProfileGenerator → Verifier
    """
    if not profile_generator:
        raise HTTPException(status_code=500, detail="Backend not initialized properly")

    client_ip = _extract_client_ip(request)
    if not rate_limiter.check(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please try again shortly.")

    if not payload.interests or payload.interests.strip() == "":
        raise HTTPException(status_code=400, detail="Please provide your interests")

    try:
        # Step 1: RAG Model - Get recommended courses based on interests
        print(f"\n[RAG] Processing user interests: {payload.interests[:100]}...")
        recommended_courses = rag_model(
            user_prompt=payload.interests,
            k=payload.num_recommendations,
            bridge=catalog_bridge,
        )
        print(f"[RAG] Recommended {len(recommended_courses)} courses: {recommended_courses[:5]}...")
        
        # Step 2: Profile Generator - Create valid profile with preferences
        print("[ProfileGen] Generating profile...")
        result = profile_generator.generate_profile(
            seed=None,  # Random each time
            preferences=recommended_courses,
            year12_choice=payload.year12_choice,
        )
        print(f"[ProfileGen] Generated profile with {len(result['courses'])} unique courses")
        print(f"[ProfileGen] Semester plan slots: {sum(len(s) for s in result['semester_plan'])}")

        # Step 3: Constraint Verifier - Validate (already done in generator, but double-check)
        print("[Verifier] Validating constraints...")
        verifier = ConstraintVerifier(result["semester_plan"], year12_choice=payload.year12_choice)
        constraints_satisfied = verifier.verify()
        print(f"[Verifier] Constraints satisfied: {constraints_satisfied}")
        
        # Format response
        details_by_code: dict[str, object] = {}
        if catalog_bridge:
            try:
                detail_rows = catalog_bridge.get_courses_by_codes(
                    [c.course_code for c in result["courses"]],
                    include_excluded=True,
                )
                details_by_code = {row.course_code: row for row in detail_rows}
            except Exception:
                details_by_code = {}

        courses_info = []
        for course in result["courses"]:
            details = details_by_code.get(course.course_code)
            course_name = (details.name if details and details.name else course_lookup.get(course.course_code, "Name not available"))
            courses_info.append(CourseInfo(
                course_code=course.course_code,
                course_name=course_name,
                course_description=details.description if details else None,
                area=course.area if course.area else -1,
                term=course.term,
                num_credits=course.num_credits,
                kernel_course=course.kernel_course,
                technical_elective=course.technical_elective,
                free_elective=bool(getattr(course, "free_elective", False)),
                course_type=getattr(course, "course_type", None),
                non_technical_type=getattr(course, "non_technical_type", None),
                ceab_math=float(getattr(course.ceab, "mathematics", 0.0)),
                ceab_ns=float(getattr(course.ceab, "natural_science", 0.0)),
                ceab_cs=float(getattr(course.ceab, "complementary_studies", 0.0)),
                ceab_es=float(getattr(course.ceab, "engineering_science", 0.0)),
                ceab_ed=float(getattr(course.ceab, "engineering_design", 0.0)),
            ))

        labels = ["3F", "3S", "4F", "4S"]
        semester_plan_payload = [
            SemesterPlanRow(term=labels[i], course_codes=[c.course_code for c in result["semester_plan"][i]])
            for i in range(4)
        ]
        
        response = ProfileResponse(
            success=True,
            courses=courses_info,
            semester_plan=semester_plan_payload,
            total_credits=result["total_credits"],
            kernel_areas_selected=result["kernel_areas_selected"],
            depth_areas_selected=result["depth_areas_selected"],
            preferences_used=result["preferences_used"],
            preferences_skipped=result["preferences_skipped"],
            constraints_satisfied=constraints_satisfied,
            generation_engine=result.get("generation_engine"),
            solver_runtime_ms=result.get("solver_runtime_ms"),
            preference_hit_count=result.get("preference_hit_count"),
            preference_weighted_score=result.get("preference_weighted_score"),
            constraint_diagnostics=result.get("constraint_diagnostics"),
        )
        gc.collect()
        return response

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        gc.collect()
        raise HTTPException(status_code=500, detail=f"Error generating profile: {str(e)}")


@app.get("/year12-courses", response_model=Year12CoursesResponse)
async def year12_courses(year12_choice: str = Query(default="ECE297H1")):
    if not catalog_bridge:
        raise HTTPException(status_code=500, detail="Backend not initialized properly")
    rows = catalog_bridge.get_profile_candidate_courses(
        include_excluded=False,
        include_year1_year2=True,
        include_required=True,
    )
    codes = sorted({r.course_code for r in rows if bool(getattr(r, "is_year1_year2", False))})
    if year12_choice.upper() == "ECE295H1":
        codes = [c for c in codes if c != "ECE297H1"]
        if "ECE295H1" not in codes:
            codes.append("ECE295H1")
    else:
        codes = [c for c in codes if c != "ECE295H1"]
        if "ECE297H1" not in codes:
            codes.append("ECE297H1")
    return Year12CoursesResponse(success=True, year12_choice=year12_choice.upper(), courses=sorted(codes))


@app.get("/courses", response_model=CourseSearchResponse)
async def search_courses(
    q: str | None = Query(default=None),
    term: str | None = Query(default=None),
    area: int | None = Query(default=None),
    kernel_course: bool | None = Query(default=None),
    technical_elective: bool | None = Query(default=None),
    free_elective: bool | None = Query(default=None),
    course_type: str | None = Query(default=None),
    non_technical_type: str | None = Query(default=None),
    min_math: float | None = Query(default=None),
    min_ns: float | None = Query(default=None),
    min_cs: float | None = Query(default=None),
    min_es: float | None = Query(default=None),
    min_ed: float | None = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=5000),
):
    if not catalog_bridge:
        raise HTTPException(status_code=500, detail="Backend not initialized properly")

    # Always build from filter_courses so query text composes with all filters.
    rows = catalog_bridge.filter_courses(
        term=term,
        area=area,
        kernel_course=kernel_course,
        course_type=course_type,
        non_technical_type=non_technical_type,
        min_math=min_math,
        min_ns=min_ns,
        min_cs=min_cs,
        min_es=min_es,
        min_ed=min_ed,
        include_excluded=False,
        limit=limit,
    )

    if technical_elective is not None:
        rows = [r for r in rows if bool(r.technical_elective) == technical_elective]
    if free_elective is not None:
        rows = [r for r in rows if bool(r.free_elective) == free_elective]

    if q and q.strip():
        needle = q.strip().lower()
        rows = [
            r for r in rows
            if needle in r.course_code.lower()
            or needle in (r.name or "").lower()
            or needle in (r.description or "").lower()
        ]

    # Cache get_course_offering by (course_code, term) to avoid redundant DB
    # calls for multi-area courses that share the same offering row.
    # IMPORTANT: we use `row` (from filter_courses) for classification fields
    # like area/kernel_course/technical_elective because filter_courses returns
    # one row per (course_code, term, area) — so multi-area courses correctly
    # appear multiple times with different areas.  get_course_offering() uses
    # LIMIT 1 and would always return the lowest area, silently collapsing all
    # area variants into a single area value.
    offering_cache: dict[tuple[str, str], object] = {}
    courses = []
    for row in rows:
        key = (row.course_code, row.term)
        if key not in offering_cache:
            offering_cache[key] = catalog_bridge.get_course_offering(row.course_code, row.term)
        offering = offering_cache[key]
        if offering is None:
            continue
        courses.append(
            CourseInfo(
                course_code=row.course_code,
                course_name=offering.name or "Name not available",
                course_description=offering.description,
                # Use the per-classification area from filter_courses, not
                # offering.area which only reflects the single lowest area.
                area=row.area if row.area is not None else -1,
                term=row.term,
                num_credits=0.5 if row.term in ("F", "S") else 1.0,
                # Use per-classification flags (may differ between area rows).
                kernel_course=bool(row.kernel_course),
                technical_elective=bool(row.technical_elective),
                free_elective=bool(row.free_elective),
                course_type=row.course_type,
                non_technical_type=row.non_technical_type,
                # CEAB is course-level; come from the cached offering.
                ceab_math=float(offering.math or 0.0),
                ceab_ns=float(offering.ns or 0.0),
                ceab_cs=float(offering.cs or 0.0),
                ceab_es=float(offering.es or 0.0),
                ceab_ed=float(offering.ed or 0.0),
            )
        )

    return CourseSearchResponse(success=True, courses=courses[:limit])


@app.post("/regenerate-profile", response_model=RegenerateProfileResponse)
async def regenerate_profile(request: Request, payload: RegenerateProfileRequest):
    """
    Regenerate a profile applying feedback (LOCK / EXCLUDE / LIKE / DISLIKE) on top of
    the original ranked preference list.

    Unlike /generate-profile, this endpoint does NOT call the ranking engine (RAG model).
    The caller is responsible for passing the original preferences list that was returned
    by the initial /generate-profile call.

    Solver timeout is 15 seconds (vs. 8 seconds for initial generation) to accommodate
    the additional hard constraints introduced by feedback.
    """
    if not profile_generator:
        raise HTTPException(status_code=500, detail="Backend not initialized properly")

    client_ip = _extract_client_ip(request)
    if not rate_limiter.check(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please try again shortly.")

    feedback = payload.feedback
    locked_set = {c.strip().upper() for c in feedback.locked if c.strip()}
    excluded_set = {c.strip().upper() for c in feedback.excluded if c.strip()}
    liked_list = [c.strip().upper() for c in feedback.liked if c.strip()]
    disliked_list = [c.strip().upper() for c in feedback.disliked if c.strip()]

    # Validate: a course cannot be both LOCK and EXCLUDE simultaneously.
    conflicts = locked_set & excluded_set
    if conflicts:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot LOCK and EXCLUDE the same course(s): {', '.join(sorted(conflicts))}",
        )

    # Validate: required non-capstone courses (e.g. ECE472H1) cannot be EXCLUDED
    # because the solver's hard constraints always force them to be selected.
    excluded_required = excluded_set & _required_noncap_codes
    if excluded_required:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot EXCLUDE required course(s): {', '.join(sorted(excluded_required))}. "
                   "These courses are mandatory in every valid ECE profile.",
        )

    # Validate: at least one capstone option must remain available.
    if _capstone_codes_pool and _capstone_codes_pool.issubset(excluded_set):
        raise HTTPException(
            status_code=422,
            detail="Cannot EXCLUDE all capstone options. At least one capstone must remain available.",
        )

    try:
        result = profile_generator.generate_profile(
            seed=None,
            preferences=payload.preferences,
            year12_choice=payload.year12_choice,
            locked_codes=list(locked_set),
            excluded_codes=list(excluded_set),
            liked_codes=liked_list,
            disliked_codes=disliked_list,
            timeout_seconds=15.0,
        )
    except SolverTimeoutError as exc:
        return RegenerateProfileResponse(
            success=False,
            timed_out=True,
            error=str(exc),
        )
    except SolverInfeasibleError as exc:
        return RegenerateProfileResponse(
            success=False,
            feedback_infeasible=True,
            error=str(exc),
        )
    except Exception as exc:
        print(f"[ERROR] Regeneration failed: {exc}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error regenerating profile: {str(exc)}")

    # Build courses_info (same pattern as /generate-profile)
    details_by_code: dict[str, object] = {}
    if catalog_bridge:
        try:
            detail_rows = catalog_bridge.get_courses_by_codes(
                [c.course_code for c in result["courses"]],
                include_excluded=True,
            )
            details_by_code = {row.course_code: row for row in detail_rows}
        except Exception:
            details_by_code = {}

    courses_info = []
    for course in result["courses"]:
        details = details_by_code.get(course.course_code)
        course_name = (
            details.name if details and details.name
            else course_lookup.get(course.course_code, "Name not available")
        )
        courses_info.append(CourseInfo(
            course_code=course.course_code,
            course_name=course_name,
            course_description=details.description if details else None,
            area=course.area if course.area else -1,
            term=course.term,
            num_credits=course.num_credits,
            kernel_course=course.kernel_course,
            technical_elective=course.technical_elective,
            free_elective=bool(getattr(course, "free_elective", False)),
            course_type=getattr(course, "course_type", None),
            non_technical_type=getattr(course, "non_technical_type", None),
            ceab_math=float(getattr(course.ceab, "mathematics", 0.0)),
            ceab_ns=float(getattr(course.ceab, "natural_science", 0.0)),
            ceab_cs=float(getattr(course.ceab, "complementary_studies", 0.0)),
            ceab_es=float(getattr(course.ceab, "engineering_science", 0.0)),
            ceab_ed=float(getattr(course.ceab, "engineering_design", 0.0)),
        ))

    labels = ["3F", "3S", "4F", "4S"]
    semester_plan_payload = [
        SemesterPlanRow(term=labels[i], course_codes=[c.course_code for c in result["semester_plan"][i]])
        for i in range(4)
    ]

    verifier = ConstraintVerifier(result["semester_plan"], year12_choice=payload.year12_choice)
    constraints_satisfied = verifier.verify()

    response = RegenerateProfileResponse(
        success=True,
        courses=courses_info,
        semester_plan=semester_plan_payload,
        total_credits=result["total_credits"],
        kernel_areas_selected=result["kernel_areas_selected"],
        depth_areas_selected=result["depth_areas_selected"],
        preferences_used=result["preferences_used"],
        preferences_skipped=result["preferences_skipped"],
        constraints_satisfied=constraints_satisfied,
        generation_engine=result.get("generation_engine"),
        solver_runtime_ms=result.get("solver_runtime_ms"),
        preference_hit_count=result.get("preference_hit_count"),
        preference_weighted_score=result.get("preference_weighted_score"),
        constraint_diagnostics=result.get("constraint_diagnostics"),
        feedback_result=FeedbackHonorReport(
            liked_honored=result.get("liked_honored", []),
            liked_skipped=result.get("liked_skipped", []),
            disliked_honored=result.get("disliked_honored", []),
            disliked_forced=result.get("disliked_forced", []),
        ),
    )
    gc.collect()
    return response


if __name__ == "__main__":
    import uvicorn
    # Render (and other cloud hosts) inject a PORT env var. Locally we default to 8000.
    port = int(os.getenv("PORT", 8000))
    print("\n" + "="*60)
    print("Starting MagellanAI API Server")
    print(f"Binding to 0.0.0.0:{port}")
    print("="*60)
    print("Make sure OPENAI_API_KEY is set in your environment!")
    print("="*60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)

