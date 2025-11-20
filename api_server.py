# api_server.py
# FastAPI server that connects frontend to backend pipeline

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import sys
import os

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from backend.ranking_engine.rag_model import rag_model
from backend.profile_generator.profile_generator import ProfileGenerator
from backend.profile_generator.technical_course_loader import TechnicalCourseLoader
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

# Load data once at startup
DATA_DIR = project_root / "data"
TECHNICAL_COURSES_PATH = DATA_DIR / "technical_courses.ods"
COURSES_DESCRIPTION_PATH = DATA_DIR / "courses_description.ods"

try:
    technical_courses = TechnicalCourseLoader.load_technical_courses(str(TECHNICAL_COURSES_PATH))
    course_lookup = load_course_details_index(str(COURSES_DESCRIPTION_PATH))
    profile_generator = ProfileGenerator(technical_courses)
    print("✓ Data loaded successfully")
except Exception as e:
    print(f"Error loading data: {e}")
    technical_courses = []
    course_lookup = {}
    profile_generator = None


class UserInterestRequest(BaseModel):
    interests: str
    num_recommendations: int = 15


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
    total_credits: float
    kernel_areas_selected: list[int]
    depth_areas_selected: list[int]
    preferences_used: list[str]
    preferences_skipped: list[str]
    constraints_satisfied: bool
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
        "num_technical_courses": len(technical_courses) if technical_courses else 0
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
            data_path=COURSES_DESCRIPTION_PATH
        )
        print(f"[RAG] Recommended {len(recommended_courses)} courses: {recommended_courses[:5]}...")
        
        # Step 2: Profile Generator - Create valid profile with preferences
        print("[ProfileGen] Generating profile...")
        result = profile_generator.generate_profile(
            seed=None,  # Random each time
            preferences=recommended_courses
        )
        print(f"[ProfileGen] Generated profile with {len(result['courses'])} courses")
        
        # Step 3: Constraint Verifier - Validate (already done in generator, but double-check)
        print("[Verifier] Validating constraints...")
        verifier = ConstraintVerifier(result["courses"])
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
        
        return ProfileResponse(
            success=True,
            courses=courses_info,
            total_credits=result["total_credits"],
            kernel_areas_selected=result["kernel_areas_selected"],
            depth_areas_selected=result["depth_areas_selected"],
            preferences_used=result["preferences_used"],
            preferences_skipped=result["preferences_skipped"],
            constraints_satisfied=constraints_satisfied
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

