# MagellanAI 🧭

An intelligent course planning Assistant for undergraduate computer and electrical engineering students at the University of Toronto: a platform that helps students explore courses, receive personalized guidance, and build course profiles that align with their interests and meet graduation requirements.

## Introduction

Course planning in the Electrical and Computer Engineering (ECE) program at the University of Toronto (UofT) has become increasingly complex due to numerous program requirements, prerequisites, breadth and depth constraints, and elective options. Magellan is a tool used by UofT ECE students to select courses and validate the requirements. While Magellan provides an essential platform for verifying degree requirements, it cannot guide students in aligning their course selections with personal interests, career goals, or minors and certificates. Students often spend considerable time iterating through trial profiles, manually checking prerequisites, and balancing competing constraints, which can result in frustration and suboptimal academic plans. To address this challenge, our project, MagellanAI, leverages AI-driven conversational interfaces and constraint satisfaction methods to automatically generate complete, valid, and personalized Magellan profiles. By integrating student goals directly into the profile generation process, MagellanAI aims to streamline course planning, save time, and improve academic decision-making for upper-year ECE students.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+ and npm
- OpenAI API Key

### 1. Setup Environment

```bash
# Clone the repository (if not already done)
cd MagellanAI

# Create .env file with your OpenAI API key
echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
```

### 2. Start Backend API Server

**Option A: Using the startup script (recommended)**
```bash
./start_backend.sh
```

**Option B: Manual start**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements_api.txt
python3 -m backend.data_pipeline.cli init-db
python3 -m backend.data_pipeline.cli migrate-from-folders --data-dir data
python3 -m backend.data_pipeline.cli scrape-missing-descriptions
python api_server.py
```

The backend will start on `http://localhost:8000`

### 3. Start Frontend (in a new terminal)

**Option A: Using the startup script (recommended)**
```bash
./start_frontend.sh
```

**Option B: Manual start**
```bash
cd frontend
npm install
npm run dev
```

The frontend will open automatically at `http://localhost:5173`

### 4. Use the Application

1. Enter your interests and goals in the text box (e.g., "I'm interested in machine learning, AI, and software engineering")
2. Click "Generate My Course Profile"
3. View your personalized 10-credit course profile with all ECE requirements satisfied!

## 📁 Project Structure

```
MagellanAI/
├── api_server.py                     # FastAPI backend server
├── frontend/                         # SvelteKit web interface
│   ├── src/
│   │   ├── routes/                  # Route pages
│   │   └── lib/                     # Shared components, types, API client
│   └── package.json
├── backend/
│   ├── ranking_engine/
│   │   └── rag_model.py             # RAG semantic search + GPT-4
│   ├── profile_generator/
│   │   └── profile_generator.py     # Constraint satisfaction algorithm
│   ├── constraint_verifier/
│   │   └── constraint_verifier.py   # Graduation requirement validation
│   └── course_query_system/
│       └── basic_query.py           # Course search utilities
├── data/
│   ├── magellan.db                  # Canonical SQLite database
│   ├── course_codes/                # Course-code source CSVs
│   ├── term/                        # Offering term source CSVs
│   ├── technical_classification/    # Technical area/kernel source CSVs
│   ├── ceab/                        # CEAB source CSVs (course-level)
│   └── excluded_course_codes.csv    # Excluded code list
└── integration_test/
    └── test_full_flow.py            # End-to-end tests
```

## 🔧 How It Works

1. **User Input**: Student describes their interests through a ChatGPT-like interface
2. **RAG Model**: Semantic search using sentence-transformers + GPT-4 reranking finds relevant courses
3. **Profile Generator**: Constraint satisfaction algorithm creates a valid 10-credit profile
4. **Constraint Verifier**: Validates all ECE graduation requirements (kernel courses, depth areas, capstone, etc.)
5. **Display Results**: Beautiful visualization of the generated course profile

## 📚 Features

- **AI-Powered Course Recommendations**: Uses RAG (Retrieval-Augmented Generation) with GPT-4
- **Constraint Satisfaction**: Guarantees valid profiles meeting all ECE requirements
- **Personalized**: Matches courses to your interests while satisfying constraints
- **Beautiful UI**: Modern, responsive design with real-time feedback
- **Detailed Visualization**: Shows required courses, depth areas, kernel courses, and preferences matched

## 🧪 Testing

```bash
# Run unit tests
python -m unittest backend/constraint_verifier/test_constraint_verifier.py
python -m unittest backend/profile_generator/test_profile_generator.py

# Run integration tests
python -m unittest integration_test/test_full_flow.py
```

## 📖 Documentation

For detailed setup instructions, troubleshooting, and architecture details, see [SETUP_INSTRUCTIONS.md](SETUP_INSTRUCTIONS.md)

## 🎓 Capstone Project Contributors

Snehal Sobti, Ishika Mittal, Hamza Mohammed, Krishna Advait Sripada

## 📝 License

This project is part of an undergraduate capstone project at the University of Toronto.
