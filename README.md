# 🏥 Insurance AI Platform

> AI-powered health insurance recommendation system with multi-agent architecture, real-time verification, and personalized recommendations for California residents.

## 📋 Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Development Phases](#development-phases)
- [Architecture](#architecture)
- [Contributing](#contributing)

---

## 🎯 Overview

This platform helps users navigate the complex world of health insurance by providing:
- **Intelligent Recommendations**: ML-powered matching based on user needs
- **Real-time Verification**: Multi-agent system ensures data accuracy
- **Comparison Tools**: Side-by-side plan comparisons with detailed breakdowns
- **AI Chatbot**: Natural language interface to find the perfect plan
- **Cost Analysis**: Monte Carlo simulations for expected costs

**Target Audience**: California residents, including special visa holders (H1B, F1, J1)

---

## ✨ Features

### Phase 1: Data Foundation ✅ (Current)
- [x] Automated web scraping for insurance plans
- [x] PostgreSQL database with optimized schema
- [x] Data validation and quality checks
- [x] Initial dataset of 20-30 California health plans

### Phase 2: ML Recommendation Engine 🚧 (In Progress)
- [ ] Custom recommendation model (XGBoost + Neural Net)
- [ ] Feature engineering (cost-to-coverage ratios, user profiles)
- [ ] Model training pipeline with MLflow tracking
- [ ] SHAP values for explainability

### Phase 3: RAG-Based Chatbot 📅 (Planned)
- [ ] Vector database (Pinecone/ChromaDB)
- [ ] Semantic search for plan discovery
- [ ] LLM-powered conversational interface
- [ ] Context-aware recommendations

### Phase 4: Multi-Agent System 📅 (Planned)
- [ ] Agent 1: Real-time data scraper
- [ ] Agent 2: Plan analyzer (ML model)
- [ ] Agent 3: Recommendation engine (RAG + LLM)
- [ ] Agent orchestration with LangGraph

### Phase 5: Production Features 📅 (Planned)
- [ ] A/B testing framework
- [ ] Model drift detection
- [ ] Cost optimization dashboard
- [ ] User authentication & profiles

---

## 🛠️ Tech Stack

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Database**: PostgreSQL 15
- **ORM**: SQLAlchemy
- **Web Scraping**: Playwright, BeautifulSoup

### ML/AI
- **ML Frameworks**: Scikit-learn, XGBoost, LightGBM
- **LLM**: OpenAI GPT-4, Anthropic Claude
- **Vector DB**: ChromaDB / Pinecone
- **MLOps**: MLflow, Prometheus, Grafana
- **Agent Framework**: LangGraph, LangChain

### Frontend (Phase 5)
- **Framework**: React 18
- **Styling**: Tailwind CSS
- **State Management**: Redux Toolkit
- **Charts**: Recharts, D3.js

### DevOps
- **Containerization**: Docker, Docker Compose
- **CI/CD**: GitHub Actions
- **Testing**: Pytest
- **Code Quality**: Black, Flake8, MyPy

---

## 📁 Project Structure

```
insurance-ai-platform/
├── database/           # Database schemas and migrations
├── scrapers/           # Web scraping modules
├── data/              # Data storage (raw, processed, manual)
├── models/            # ML models and training scripts
├── api/               # FastAPI backend
├── agents/            # AI agent implementations
├── frontend/          # React application
├── tests/             # Test suites
├── notebooks/         # Jupyter notebooks for exploration
├── scripts/           # Utility scripts
├── config/            # Configuration files
└── docs/              # Documentation
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Docker Desktop
- Git
- PostgreSQL (or use Docker)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/insurance-ai-platform.git
   cd insurance-ai-platform
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Install Python dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers**
   ```bash
   playwright install chromium
   ```

5. **Start PostgreSQL database**
   ```bash
   docker-compose up -d
   ```

6. **Verify database setup**
   ```bash
   docker exec -it insurance_db psql -U postgres -d insurance_db -c "\dt"
   ```

7. **Run the scraper (optional)**
   ```bash
   python scrapers/covered_ca_scraper.py
   ```

---

## 📊 Development Phases

### ✅ Phase 1: Data Foundation (Weeks 1-2)
**Goal**: Establish data collection and storage
- Set up PostgreSQL database
- Build web scraper for Covered California
- Collect initial dataset of 20-30 plans
- Implement data validation

**Key Deliverables**:
- `database/schema.sql` - Complete database schema
- `scrapers/covered_ca_scraper.py` - Production-ready scraper
- Initial dataset in JSON/CSV format

### 🚧 Phase 2: ML Model (Weeks 3-4)
**Goal**: Build recommendation engine
- Exploratory data analysis
- Feature engineering
- Train classification model
- Set up MLflow for experiment tracking

**Key Deliverables**:
- `models/recommendation_model.py` - Trained model
- `notebooks/02_model_development.ipynb` - Model development process
- Model evaluation metrics and reports

### 📅 Phase 3: RAG System (Weeks 5-6)
**Goal**: Implement conversational AI
- Set up vector database
- Create embeddings for all plans
- Build RAG pipeline
- Implement chatbot interface

### 📅 Phase 4: Multi-Agent System (Weeks 7-8)
**Goal**: Real-time verification and orchestration
- Implement 3 specialized agents
- Agent communication and orchestration
- Real-time data verification
- Confidence scoring system

### 📅 Phase 5: Production & MLOps (Weeks 9-10)
**Goal**: Deploy and monitor
- Docker deployment
- Monitoring dashboard
- A/B testing framework
- CI/CD pipeline

---

## 🏗️ Architecture

### High-Level Architecture
```
┌─────────────┐
│   Frontend  │ (React)
└──────┬──────┘
       │
┌──────▼──────┐
│  API Layer  │ (FastAPI)
└──────┬──────┘
       │
   ┌───┴────┬──────────┬──────────┐
   │        │          │          │
┌──▼───┐ ┌─▼────┐ ┌───▼────┐ ┌──▼──────┐
│Agent1│ │Agent2│ │ Agent3 │ │   DB    │
│Scraper│ │Analyzer│ │Recomm. │ │Postgres │
└──────┘ └──────┘ └────────┘ └─────────┘
```

### Data Flow
```
User Query → Chatbot → Vector Search → ML Model → 
→ Verification Agent → Confidence Score → Response
```

---

## 📈 Performance Metrics

*Metrics will be added as features are developed*

- **Scraping Success Rate**: TBD
- **Model Accuracy**: TBD
- **API Latency (p99)**: TBD
- **Data Freshness**: TBD

---

## 🧪 Testing

Run all tests:
```bash
pytest tests/
```

Run with coverage:
```bash
pytest --cov=. --cov-report=html
```

---

## 📝 License

MIT License - See LICENSE file for details

---

## 🤝 Contributing

This is a portfolio project, but feedback is welcome!

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

---

## 📧 Contact

**Rushy** - [Your LinkedIn] - [Your Email]

Project Link: [https://github.com/RushyanthN/insurance-ai-platform](https://github.com/yourusername/insurance-ai-platform)

---

## 🙏 Acknowledgments

- Covered California for public insurance data
- Anthropic Claude for AI assistance
- Open source community

---

**Built with ❤️ for helping people find the right insurance**