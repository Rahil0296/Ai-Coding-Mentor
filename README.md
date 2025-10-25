# 🤖 Agentic AI Coding Mentor

**(Work in Progress)**

An AI-powered coding education platform that provides personalized, adaptive programming instruction. The system tracks user progress, adapts to individual learning styles, and offers real-time feedback with comprehensive analytics.

## 🌟 Current Features

- **Personalized Learning**: Adapts to user's programming language preference, learning style, and experience level
- **3 Teaching Modes**: 
  - *Guided* - Helpful explanations with hints
  - *Debug Practice* - Intentionally buggy code for learning
  - *Perfect Mode* - Production-ready code standards
- **Learning Analytics Dashboard**: Track progress across 9+ KPIs including success rates, confidence trends, topic exploration, and learning streaks
- **User Profiles & History**: Persistent context-aware conversations that remember your learning journey
- **Code Execution Sandbox**: Safe execution environment for Python, JavaScript, and Bash
- **Dynamic Roadmaps**: AI-generated learning paths tailored to your goals
- **Streaming Responses**: Real-time token streaming for natural conversation flow

## 🚧 Planned Features

- **Self-Improving Agent**: Trace logging and pattern detection to learn from past interactions (data collection active)
- **Enhanced ReAct Architecture**: Multi-step reasoning and action loops for complex problem-solving
- **React Frontend**: Modern, responsive UI with real-time analytics visualizations
- **Real-time Code Collaboration**: Multi-user learning sessions
- **Advanced Debugging Assistance**: Step-by-step debugging guidance

## 🏗️ Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  React Frontend │────▶│ FastAPI Backend │────▶│    PostgreSQL   │
│  (Coming Soon)  │      │  (Operational)  │      │    Database     │
└─────────────────┘      └─────────────────┘      └─────────────────┘
                                │
                                ▼
                        ┌─────────────────┐
                        │  Ollama (Local) │
                        │  Qwen2.5-Coder  │
                        └─────────────────┘
```

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL
- Ollama with Qwen2.5-Coder model
- Node.js (for code execution features)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Rahil0296/ai-coding-mentor.git
   cd ai-coding-mentor
   ```

2. **Set up Python environment**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   # Create .env file in backend directory
   cp .env.example .env
   ```
   
   Edit `.env` with your configuration:
   ```env
   DATABASE_URL=postgresql://username:password@localhost:5432/agentic_db
   OLLAMA_BASE_URL=http://127.0.0.1:11434
   OLLAMA_MODEL=qwen25_coder_7b_local:latest
   ```

4. **Set up the database**
   ```bash
   python init_db.py
   ```

5. **Install and run Ollama**
   ```bash
   # Install Ollama from https://ollama.ai
   ollama pull qwen2.5-coder:7b
   ```

6. **Start the backend server**
   ```bash
   uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000`

## 📚 API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Key Endpoints

#### User Management
- `POST /users/onboard` - Create user profile with learning preferences
- `GET /users/{user_id}` - Retrieve user profile

#### Learning
- `POST /ask` - Stream AI responses with personalized teaching
- `POST /roadmaps` - Create/retrieve personalized learning roadmaps

#### Analytics
- `GET /analytics/{user_id}` - Comprehensive learning analytics
- `GET /analytics/{user_id}/summary` - Quick stats summary

#### Code Execution
- `POST /execute` - Execute code in sandboxed environment

#### Health
- `GET /health` - Check service status

## 📊 Analytics Dashboard

The platform tracks comprehensive learning metrics:

- **Question Activity**: Total questions, weekly trends, daily breakdown
- **Performance Metrics**: Success rate, average confidence scores
- **Learning Patterns**: Top topics explored, teaching mode preferences
- **Engagement**: Current and longest learning streaks
- **Time Investment**: Estimated total learning hours

Access via: `GET /analytics/{user_id}`

## 🧠 Teaching Modes

### Guided Mode (Default)
- Helpful explanations with context
- Encourages understanding over memorization
- Provides hints and step-by-step breakdowns

### Debug Practice Mode
- Presents code with intentional bugs
- Develops debugging skills
- Encourages critical thinking

### Perfect Mode
- Production-ready code standards
- Emphasis on best practices
- Clean, optimized solutions

## 🔒 Security Features

- **Sandboxed Code Execution**: Isolated environment with timeout limits
- **Module Restrictions**: Blocks dangerous Python imports (os, subprocess, socket)
- **Command Whitelisting**: Only safe bash commands allowed
- **Input Validation**: Comprehensive request validation with Pydantic
- **SQL Injection Prevention**: Parameterized queries via SQLAlchemy ORM
- **No External Network Access**: Code execution is network-isolated

## 🛠️ Development

### Running Tests
```bash
cd backend
pytest tests/
```

### Code Style
```bash
# Format code
black backend/

# Lint
flake8 backend/
```

### Database Migrations
```bash
# Add new models without dropping data
python update_db.py
```

## 📈 Performance

- **Query Response Time**: < 1s for analytics with 1000+ records
- **Code Generation**: ~18-30s average (local LLM)
- **Concurrent Users**: Tested with 10+ simultaneous requests
- **Database**: Optimized indexes for sub-second queries


## 🤝 Contributing

This is currently a portfolio project demonstrating advanced AI application development. Feedback and suggestions are welcome!

## 📝 Tech Stack

**Backend:**
- FastAPI (async Python web framework)
- SQLAlchemy (ORM)
- PostgreSQL (database)
- Pydantic (validation)

**AI/ML:**
- Ollama (local LLM inference)
- Qwen 2.5 Coder 7B (code generation)

**DevOps (Planned):**
- Docker & Docker Compose
- AWS (App Runner / Lambda)
- GitHub Actions (CI/CD)

**Frontend (Planned):**
- React + TypeScript
- Tailwind CSS
- Chart.js / Recharts (analytics visualization)

---

**Note**: This is an active development project showcasing modern AI application architecture, secure API design, and production-ready backend development practices.
