# 🤖 Agentic AI Coding Mentor

**(Production Features Added!)**

An AI-powered coding education platform that provides personalized, adaptive programming instruction. The system tracks user progress, adapts to individual learning styles, and offers real-time feedback with comprehensive analytics.

**NEW: Now includes enterprise-grade production monitoring, security, and logging!**

## Current Features

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

## 🚀 NEW Production Features:

- **🏥 Health Monitoring**: Comprehensive system health checks with database connectivity, resource monitoring, and service status
- **🚦 API Rate Limiting**: Production security with Redis backend and graceful in-memory fallback (10 req/min analytics, 20 req/5min AI)
- **📋 Structured Logging**: JSON logs with request tracing, performance metrics, and error tracking
- **📚 Enhanced API Documentation**: Professional Swagger UI with examples, rate limiting info, and interactive testing

## 🚧 My Planned Features :

- **Self-Improving Agent**: Trace logging and pattern detection to learn from past interactions (data collection active)
- **Enhanced ReAct Architecture**: Multi-step reasoning and action loops for complex problem-solving
- **React Frontend**: Modern, responsive UI with real-time analytics visualizations
- **Real-time Code Collaboration**: Multi-user learning sessions
- **Advanced Debugging Assistance**: Step-by-step debugging guidance

## 🏗️ The Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  React Frontend │────▶│| FastAPI Backend |│────▶│    PostgreSQL   │
│  (Coming Soon)  │      │                 │      │    Database     │
└─────────────────┘      │                 │      └─────────────────┘
                         └─────────────────┘              │
                                │                         │
                                ▼                         ▼
                        ┌─────────────────┐      ┌─────────────────┐
                        │  Ollama (Local) │      │ Redis (Optional)│
                        │  Qwen2.5-Coder  │      │  Rate Limiting  │
                        └─────────────────┘      └─────────────────┘
```

## 🚀 How to get started on your device : 

### Prerequisites

- Python 3.11+
- PostgreSQL
- Ollama with Qwen2.5-Coder model
- Node.js (for code execution features)
- Redis (optional, for distributed rate limiting)

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
   # Optional: Redis for distributed rate limiting
   REDIS_URL=redis://localhost:6379
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
- **Enhanced Swagger UI**: `http://localhost:8000/docs` *(now with examples and rate limiting info!)*
- **ReDoc**: `http://localhost:8000/redoc`

### Key Endpoints

#### 🏥 Health & Monitoring
- `GET /health/` - Comprehensive health check with system metrics
- `GET /health/quick` - Lightweight health check for load balancers
- `GET /health/ready` - Kubernetes-style readiness check
- `GET /health/live` - Kubernetes-style liveness check

#### User Management
- `POST /users/onboard` - Create user profile with learning preferences
- `GET /users/{user_id}` - Retrieve user profile

#### Learning (Rate Limited)
- `POST /ask` - Stream AI responses with personalized teaching *(20 requests per 5 minutes)*
- `POST /roadmaps` - Create/retrieve personalized learning roadmaps

#### Analytics (Rate Limited)
- `GET /analytics/{user_id}` - Comprehensive learning analytics *(10 requests per minute)*
- `GET /analytics/{user_id}/summary` - Quick stats summary *(30 requests per minute)*

#### Code Execution (Rate Limited)
- `POST /execute` - Execute code in sandboxed environment *(10 requests per 5 minutes)*

## 🔧 Production Monitoring

### Health Checks
The system now provides multiple health endpoints for different monitoring scenarios:

```bash
# Comprehensive health (for monitoring dashboards)
curl http://localhost:8000/health/

# Quick check (for load balancers)
curl http://localhost:8000/health/quick

# Kubernetes readiness
curl http://localhost:8000/health/ready
```

### Logging
All requests are logged in structured JSON format with:
- Request IDs for tracing
- Performance metrics
- Error tracking
- System resource monitoring

Logs are saved to `backend/logs/app.log`

### Rate Limiting
- **Analytics**: 10 requests per minute per IP
- **AI Questions**: 20 requests per 5 minutes per IP  
- **Code Execution**: 10 requests per 5 minutes per IP
- **Global Limit**: 1000 requests per hour per IP

Rate limit headers are included in all responses.

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
- **Rate Limiting**: Prevents API abuse and ensures fair usage
- **Request Tracing**: All requests logged with unique IDs

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

### View Logs
```bash
# Real-time structured logs
tail -f backend/logs/app.log

# Performance metrics
curl http://localhost:8000/admin/performance
```

## 📈 Performance

- **Query Response Time**: < 1s for analytics with 1000+ records
- **Code Generation**: ~18-30s average (local LLM)
- **Concurrent Users**: Tested with 10+ simultaneous requests
- **Database**: Optimized indexes for sub-second queries
- **Health Checks**: < 2s comprehensive system check
- **Rate Limiting**: Negligible overhead with Redis backend

## 🤝 Contributing

This is currently a portfolio project demonstrating advanced AI application development with production-ready features. Feedback and suggestions are welcome!

## 📝 Tech Stack

**Backend:**
- FastAPI (async Python web framework)
- SQLAlchemy (ORM)
- PostgreSQL (database)
- Pydantic (validation)
- Redis (rate limiting, optional)

**AI/ML:**
- Ollama (local LLM inference)
- Qwen 2.5 Coder 7B (code generation)

**Production Features:**
- Structured logging with JSON format
- Health monitoring with system metrics
- Rate limiting with graceful fallback
- Professional API documentation

**DevOps (Planned):**
- Docker & Docker Compose
- AWS (App Runner / Lambda)
- GitHub Actions (CI/CD)

**Frontend (Planned):**
- React + TypeScript
- Tailwind CSS
- Chart.js / Recharts (analytics visualization)

---

**Note**: This is an active development project showcasing modern AI application architecture, secure API design, and **production-ready backend development practices** including monitoring, security, and observability.
