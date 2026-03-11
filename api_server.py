# api_server.py
# FastAPI server that connects frontend to backend pipeline

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from backend.ranking_engine.rag_model import rag_model
from backend.data_bridge.factory import get_catalog_bridge
from backend.profile_generator.profile_generator import ProfileGenerator
from backend.profile_generator.profile_course_loader import ProfileCourseLoader
from backend.constraint_verifier.constraint_verifier import ConstraintVerifier
from backend.course_query_system.basic_query import load_course_details_index

app = FastAPI(title="MagellanAI API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
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
    print("[ProfileGen] Strategy: cp_sat")
    print("✓ Data loaded successfully")
except Exception as e:
    print(f"Error loading data: {e}")
    catalog_bridge = None
    profile_courses = []
    course_lookup = {}
    profile_generator = None


class UserInterestRequest(BaseModel):
    interests: str
    num_recommendations: int = 15
    year12_choice: str | None = None


class SemesterPlanRow(BaseModel):
    term: str  # "3F", "3S", "4F", "4S"
    course_codes: list[str]


class CourseInfo(BaseModel):
    course_code: str
    course_name: str
    area: int
    num_credits: float
    kernel_course: bool
    technical_elective: bool


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
        "num_profile_courses": len(profile_courses) if profile_courses else 0
    }


@app.post("/generate-profile", response_model=ProfileResponse)
async def generate_profile(request: UserInterestRequest):
    """
    Main endpoint: Takes user interests, runs RAG → ProfileGenerator → Verifier
    """
    if not profile_generator:
        raise HTTPException(status_code=500, detail="Backend not initialized properly")
    
    if not request.interests or request.interests.strip() == "":
        raise HTTPException(status_code=400, detail="Please provide your interests")
    
    try:
        # Step 1: RAG Model - Get recommended courses based on interests
        print(f"\n[RAG] Processing user interests: {request.interests[:100]}...")
        recommended_courses = rag_model(
            user_prompt=request.interests,
            k=request.num_recommendations,
            bridge=catalog_bridge,
        )
        print(f"[RAG] Recommended {len(recommended_courses)} courses: {recommended_courses[:5]}...")
        
        # Step 2: Profile Generator - Create valid profile with preferences
        print("[ProfileGen] Generating profile...")
        result = profile_generator.generate_profile(
            seed=None,  # Random each time
            preferences=recommended_courses,
            year12_choice=request.year12_choice,
        )
        print(f"[ProfileGen] Generated profile with {len(result['courses'])} unique courses")
        print(f"[ProfileGen] Semester plan slots: {sum(len(s) for s in result['semester_plan'])}")

        # Step 3: Constraint Verifier - Validate (already done in generator, but double-check)
        print("[Verifier] Validating constraints...")
        verifier = ConstraintVerifier(result["semester_plan"], year12_choice=request.year12_choice)
        constraints_satisfied = verifier.verify()
        print(f"[Verifier] Constraints satisfied: {constraints_satisfied}")
        
        # Format response
        courses_info = []
        for course in result["courses"]:
            course_name = course_lookup.get(course.course_code, "Name not available")
            courses_info.append(CourseInfo(
                course_code=course.course_code,
                course_name=course_name,
                area=course.area if course.area else -1,
                num_credits=course.num_credits,
                kernel_course=course.kernel_course,
                technical_elective=course.technical_elective
            ))

        labels = ["3F", "3S", "4F", "4S"]
        semester_plan_payload = [
            SemesterPlanRow(term=labels[i], course_codes=[c.course_code for c in result["semester_plan"][i]])
            for i in range(4)
        ]
        
        return ProfileResponse(
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
        
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating profile: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("Starting MagellanAI API Server")
    print("="*60)
    print("Make sure OPENAI_API_KEY is set in your environment!")
    print("="*60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)

