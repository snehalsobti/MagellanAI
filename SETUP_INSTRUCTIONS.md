# MagellanAI - Setup & Run Instructions

## Prerequisites
- Python 3.8+
- Node.js 16+ and npm
- OpenAI API Key

---

## Backend Setup

### 1. Install Python Dependencies

```bash
# Navigate to project root
cd MagellanAI

# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install base requirements
pip install -r requirements.txt

# Install API server requirements
pip install -r requirements_api.txt
# Create .env file
echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
# From project root
python api_server.py
```

The API will start on `http://localhost:8000`

You should see:
```
Starting MagellanAI API Server
✓ Data loaded successfully
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 2.5 Initialize the database (skip this step if magellan.db is already up to date)

If `magellan.db` is already present and up to date in your repo, you can skip this step.

```bash
python3 -m backend.data_pipeline.cli init-db
python3 -m backend.data_pipeline.cli migrate-from-folders --data-dir data
python3 -m backend.data_pipeline.cli validate
```

To add a new course directly to the DB (no ODS edits required):

```bash
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

`upsert-course` behaves insert-first:
- If `(course_code, term)` already exists, CLI reports it and makes no change.
- For a new offering, CLI scrapes course name and description from UofT calendars.
- If scraping fails, insertion is aborted with an error.
- Use `--allow-update` only when you explicitly want to overwrite an existing offering.

---

## Frontend Setup

### 1. Install Node Dependencies

Open a **NEW terminal window** and run:

```bash
# Navigate to frontend folder
cd MagellanAI/frontend

# Install dependencies
npm install

./start_frontend.sh
```

### 2. Start the Frontend Development Server

```bash
# From frontend folder
npm run dev
```

The app will open automatically at `http://localhost:5173`

---

## Using MagellanAI

1. **Enter Your Interests**: In the text box, describe your academic interests, career goals, and preferred course topics
   
   Example:
   ```
   I'm interested in machine learning, artificial intelligence, and software engineering. 
   I want to build intelligent systems and work on cutting-edge AI technologies.
   I also enjoy systems programming and distributed computing.
   ```

2. **Generate Profile**: Click "Generate My Course Profile"

3. **View Results**: The system will:
   - Use RAG (Retrieval-Augmented Generation) to find relevant courses
   - Generate a valid 10-credit profile that satisfies all ECE requirements
   - Show required courses, depth areas, kernel courses, and preferences matched

---

## Architecture Flow

```
User Input (Frontend)
    ↓
POST /generate-profile (API Server)
    ↓
RAG Model (ranking_engine/rag_model.py)
    → Semantic search + GPT-4 reranking
    → Returns recommended course codes
    ↓
Profile Generator (profile_generator/profile_generator.py)
    → Constraint satisfaction algorithm
    → Generates valid 10-credit profile
    ↓
Constraint Verifier (constraint_verifier/constraint_verifier.py)
    → Validates all ECE requirements
    ↓
Response (Frontend Display)
    → Shows courses grouped by category
    → Displays statistics and preferences matched
```

---

## Troubleshooting

### Backend Issues

**"ModuleNotFoundError"**
```bash
pip install -r requirements.txt
pip install -r requirements_api.txt
```

**"OPENAI_API_KEY not set"**
```bash
# Make sure .env file exists or export the key
export OPENAI_API_KEY="sk-..."
```

**"Data missing / DB not initialized"**
```bash
# Make sure you're running from the project root and initialize DB
cd MagellanAI
python3 -m backend.data_pipeline.cli init-db
python3 -m backend.data_pipeline.cli migrate-from-folders --data-dir data
python3 -m backend.data_pipeline.cli scrape-missing-descriptions
python api_server.py
```

### Frontend Issues

**"Failed to generate profile"**
- Check that backend is running on port 8000
- Check browser console for detailed errors
- Verify OPENAI_API_KEY is set in backend

**Port Already in Use**
```bash
# Frontend (port 5173)
npx kill-port 5173

# Backend (port 8000)
npx kill-port 8000
```

---

## Testing

### Test Backend API

```bash
# Check health
curl http://localhost:8000/health

# Test profile generation
curl -X POST http://localhost:8000/generate-profile \
  -H "Content-Type: application/json" \
  -d '{"interests": "machine learning and AI", "num_recommendations": 15}'
```

### Run Existing Tests

```bash
# From project root
python -m unittest backend/constraint_verifier/test_constraint_verifier.py
python -m unittest backend/profile_generator/test_profile_generator.py
python -m unittest integration_test/test_full_flow.py
```

---

## Project Structure

```
MagellanAI/
├── api_server.py                 # FastAPI backend server (NEW)
├── requirements.txt              # Base Python dependencies
├── requirements_api.txt          # API server dependencies (NEW)
├── frontend/                     # SvelteKit frontend
│   ├── static/
│   ├── src/
│   │   ├── routes/              # Page routes
│   │   └── lib/                 # Shared components and API modules
│   └── package.json
├── backend/
│   ├── ranking_engine/
│   │   └── rag_model.py         # RAG semantic search
│   ├── profile_generator/
│   │   └── profile_generator.py # Constraint satisfaction
│   ├── constraint_verifier/
│   │   └── constraint_verifier.py # Validation
│   └── course_query_system/
├── data/
│   ├── magellan.db             # Canonical SQLite DB
│   ├── course_codes/           # Course code source CSVs
│   ├── term/                   # Term source CSVs
│   ├── technical_classification/ # Technical area/kernel source CSVs
│   ├── ceab/                   # CEAB source CSVs
│   └── excluded_course_codes.csv
└── integration_test/
```

---

## Notes

- The RAG model caches embeddings in `.rag_cache/` - first run may be slower
- Profile generation is randomized each time (no seed parameter in API)
- The system enforces all UofT ECE graduation requirements
- Preferences are "soft" - the system tries to use them but prioritizes constraint satisfaction

---

## Contributors

Snehal Sobti, Ishika Mittal, Hamza Mohammed, Krishna Advait Sripada

