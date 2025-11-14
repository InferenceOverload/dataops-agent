# DataOps Agent

**Intelligent Multi-Agent System for Data Engineering Workflows**

A production-grade orchestrator that dynamically routes data engineering tasks to specialized AI agent workflows using LangGraph and LangChain.

---

## 🎯 Overview

DataOps Agent is an intelligent orchestration system that:
- **Understands natural language queries** about data engineering tasks
- **Routes to specialized workflows** (simple queries, complex analysis, iterative refinement)
- **Manages multi-agent coordination** using supervisor patterns
- **Provides production-ready infrastructure** for deployment at scale

### Architecture

```
User Query → Main Orchestrator
                ↓
    [Intent Classification]
         ↙    ↓    ↘
      Meta  Simple  Complex
       ↓      ↓       ↓
    Help  Single  Multi-Agent
           Agent   Workflows
              ↓       ↓
           [Results]
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Anthropic API key ([Get one here](https://console.anthropic.com/))

### Installation

```bash
# Clone the repository
cd dataops-agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Run Locally

```bash
# Test individual workflows
python workflows/workflow_a.py

# Run full orchestrator
python main.py

# Start LangGraph dev server
langgraph dev
# Open http://localhost:2024/docs
```

---

## 📁 Project Structure

```
dataops-agent/
├── src/                      # Production source code (future)
│   ├── api/                 # REST API layer
│   ├── services/            # Business logic
│   ├── models/              # Data models
│   ├── core/                # Core orchestrator
│   ├── workflows/           # Workflow definitions
│   └── utils/               # Utilities
│
├── infrastructure/          # Infrastructure as Code
│   ├── terraform/          # Terraform configs
│   ├── docker/             # Dockerfiles
│   ├── kubernetes/         # K8s manifests
│   └── scripts/            # Deployment scripts
│
├── core/                    # Current POC orchestrator
│   ├── orchestrator.py     # Main orchestrator LangGraph
│   └── workflow_registry.py # Workflow registry
│
├── workflows/               # Current POC workflows
│   ├── workflow_a.py       # Simple agent
│   ├── workflow_b.py       # Supervisor pattern
│   └── workflow_c.py       # Iterative loop
│
├── tests/                   # Test suite
├── docs/                    # Documentation
├── .claude/                 # Claude Code configuration
│   └── skills/             # Development skills
│       └── langgraph-builder.md
│
└── [config files]
```

---

## 🤖 Available Workflows

### 1. Simple Agent (`workflow_a`)
**Use Case:** Basic queries, single-step tasks

**Example:** "What is LangGraph?"

**Pattern:** Single LLM call → Response

### 2. Supervisor Pattern (`workflow_b`)
**Use Case:** Complex tasks requiring research + analysis

**Example:** "Research cloud computing and analyze its benefits"

**Pattern:** Supervisor coordinates multiple specialist agents

### 3. Iterative Refinement (`workflow_c`)
**Use Case:** Progressive improvement, multi-iteration analysis

**Example:** "Iteratively develop an analysis of AI safety"

**Pattern:** Loop with artifacts, refinement over 3 iterations

### 4. Meta Queries
**Use Case:** Questions about the system itself

**Example:** "What workflows do you have?"

**Pattern:** Direct system response, no workflow invocation

---

## 🎓 Using the LangGraph Builder Skill

The project includes a Claude Code skill for LangGraph development:

```bash
# Skills are automatically loaded from .claude/skills/
# To use: Simply work with LangGraph code in this repo
```

The skill provides:
- LangGraph patterns and best practices
- Multi-agent architecture guidance
- Production code templates
- Error handling patterns
- Testing strategies

---

## 🏗️ Production Roadmap

### Phase 1: Infrastructure (Current)
- [x] POC orchestrator working
- [x] Meta-query handling
- [x] Infrastructure directories
- [x] LangGraph skill
- [ ] Docker containerization
- [ ] Terraform for AWS/GCP
- [ ] Kubernetes deployment

### Phase 2: API Layer
- [ ] FastAPI REST endpoints
- [ ] WebSocket streaming
- [ ] Authentication (API keys, JWT)
- [ ] Rate limiting
- [ ] Request validation

### Phase 3: Persistence
- [ ] PostgreSQL for workflow definitions
- [ ] Redis for caching
- [ ] S3 for artifacts
- [ ] Conversation history
- [ ] Checkpointing for long-running tasks

### Phase 4: Observability
- [ ] Structured logging (JSON)
- [ ] Metrics (Prometheus)
- [ ] Tracing (OpenTelemetry)
- [ ] Dashboards (Grafana)
- [ ] Alerting

### Phase 5: Advanced Features
- [ ] Hot-reload workflows
- [ ] Workflow versioning
- [ ] Multi-tenancy
- [ ] Human-in-the-loop approvals
- [ ] Async execution
- [ ] Workflow chaining

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Test specific workflows
pytest tests/test_workflows.py -v

# Integration tests
pytest tests/test_orchestrator.py -v

# Test meta-queries
python test_meta_query.py
```

---

## 📊 Monitoring & Observability

### Current (POC)
- Console logging
- Basic error handling
- Execution time tracking

### Planned (Production)
- Structured logging to CloudWatch/DataDog
- Prometheus metrics
- OpenTelemetry tracing
- LLM token usage tracking
- Performance dashboards

---

## 🔒 Security

### Current
- API keys in `.env` (local only)

### Planned
- AWS Secrets Manager / GCP Secret Manager
- IAM roles for services
- Network policies in K8s
- Rate limiting per tenant
- Input validation and sanitization

---

## 🚢 Deployment

### Local Development
```bash
langgraph dev
```

### Docker (Planned)
```bash
docker build -t dataops-agent .
docker run -p 8000:8000 dataops-agent
```

### Kubernetes (Planned)
```bash
kubectl apply -f infrastructure/kubernetes/
```

### Terraform (Planned)
```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

---

## 📖 Documentation

- [Setup Guide](SETUP.md) - Detailed setup instructions
- [Architecture](docs/architecture.md) - System architecture
- [Research Notes](docs/research_notes.md) - LangGraph research
- [Improvements](docs/IMPROVEMENTS.md) - Recent enhancements
- [LangGraph Skill](.claude/skills/langgraph-builder.md) - Development guide

---

## 🤝 Contributing

This project uses:
- **LangGraph** for multi-agent orchestration
- **LangChain** for LLM integrations
- **Anthropic Claude** as the LLM provider
- **Python 3.10+** with type hints
- **pytest** for testing

Development workflow:
1. Create feature branch
2. Add tests
3. Ensure tests pass
4. Submit PR

---

## 📝 License

MIT License - See LICENSE file

---

## 🔗 Resources

- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [LangChain Docs](https://python.langchain.com/)
- [Anthropic Claude](https://www.anthropic.com/claude)

---

## 💡 Example Queries

### Meta Queries
```
"What workflows do you have?"
"What can you do?"
"Help"
```

### Simple Queries
```
"What is data engineering?"
"Explain ETL processes"
```

### Complex Queries
```
"Research modern data stack tools and analyze their tradeoffs"
"Investigate data quality frameworks and compare approaches"
```

### Iterative Queries
```
"Iteratively develop a comprehensive data governance strategy"
"Progressively refine a data architecture design"
```

---

**Built for Data Engineers, by Data Engineers** 🚀
