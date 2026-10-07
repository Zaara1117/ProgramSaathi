# ProgramSaathi — AI Program & Project Management Agent

> **ProgramSaathi** is an enterprise-grade, agentic AI system for program, project, and product management. It is designed to act as an intelligent, proactive technical partner that tracks projects, digests documentation, enforces governance, analyzes scope changes, and preserves authoritative state with strict human-in-the-loop oversight.

---

## 🏛️ System Architecture & Responsibilities

ProgramSaathi strictly enforces architectural boundaries across its stack:

| Component | Responsibility | Constraints |
| :--- | :--- | :--- |
| **Azure OpenAI / Microsoft Foundry** | Reasoning, interpretation, synthesis, and structured tool selection | **NEVER** executes SQL directly; **NEVER** mutates project state silently. |
| **Azure Blob Storage** | Document Lake storing original uploaded files (PRDs, specs, transcripts, XLSX) | Immutable document preservation. |
| **Azure AI Search** | Document chunking, hybrid BM25 + vector search, evidence retrieval | Read-only grounded context for reasoning. |
| **Azure SQL Database** | Authoritative structured project state, decisions, and immutable audit log | ACID transactions; relational integrity; audit trails. |
| **Python Core** | Orchestration, validation, security guardrails, business rules, tool dispatch | Clean interface boundaries; Repository Pattern. |
| **Human-in-the-Loop** | Formal approval gate for all consequential state changes | AI can propose; only humans can approve and ratify. |

### Consequential Mutation Lifecycle
Every state change follows this immutable progression:
```
AI Recommendation ➔ Proposed Change ➔ Validation ➔ Human Approval ➔ Python Transaction ➔ SQL Update ➔ Audit Event Record
```

---

## 📂 Repository Structure

```
ProgramSaathi/
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore configuration
├── pyproject.toml            # Build configuration & dependency definitions
├── README.md                 # Project documentation and guide
│
├── src/programsaathi/        # Core Python package
│   ├── orchestrator/         # ProgramSaathi master orchestrator
│   ├── models/               # Domain entities (Pydantic v2)
│   ├── services/             # Clean service abstractions (Foundry, Blob, Search, SQL)
│   ├── repositories/         # Repository pattern for SQL & storage operations
│   ├── tools/                # Tool framework with human approval gates
│   ├── security/             # Guardrails & SQL injection prevention
│   ├── agents/               # Specialized agent workflows (when justified)
│   ├── workflows/            # High-level business workflows (Intake, Planning, Risk)
│   ├── prompts/              # System prompts & instruction templates
│   ├── config.py             # Pydantic Settings configuration loader
│   ├── exceptions.py         # Explicit domain exception hierarchy
│   ├── logging.py            # Structured JSON & console logging
│   └── main.py               # Application bootstrap entry point
│
├── tests/                    # Test suite
│   ├── conftest.py           # Pytest shared fixtures
│   ├── unit/                 # Domain model, config, tool, and service tests
│   ├── integration/          # Workflow and state lifecycle integration tests
│   └── security/             # Guardrails and injection prevention tests
│
├── database/                 # SQL database scripts
│   ├── schema.sql            # Authoritative Azure SQL DDL (17 tables)
│   ├── seed.sql              # Initial baseline seed data
│   └── migrations/           # Database migration files
│
├── infrastructure/           # Azure provisioning scripts
│   ├── azure/                # Bicep / ARM / Terraform infrastructure
│   └── scripts/              # Setup automation scripts
│
├── evaluation/               # Agent evaluation benchmarks
│   ├── datasets/             # Test PRDs, transcripts, test suites
│   ├── scenarios/            # Multi-turn project management scenarios
│   ├── retrieval/            # Grounding and search evaluation
│   ├── grounding/            # Factuality and hallucination checks
│   ├── tool_use/             # Function-calling accuracy benchmarks
│   └── memory/               # Long-term context & decision recall benchmarks
│
├── docs/                     # Architecture and operational documentation
│   └── architecture.md       # Detailed technical design & diagrams
│
└── samples/                  # Sample project artifacts
    └── sample_prd.md         # Example PRD document
```

---

## 📦 Domain Entities (Phase 1 Baseline)

ProgramSaathi implements 17 core domain models backed by Pydantic v2 validation:

1. **`Project`**: Root container for project objectives, timelines, and budgets.
2. **`Milestone`**: Major delivery gates and target delivery deadlines.
3. **`Stakeholder`**: Team leads, sponsors, and authorized decision approvers.
4. **`Requirement`**: Functional, non-functional, security, and compliance requirements.
5. **`UserStory`**: Agile user stories with persona statements and story points.
6. **`Task`**: Discrete engineering or operational work items.
7. **`Dependency`**: Inter-item relationship graphs (`BLOCKS`, `BLOCKED_BY`, `RELATES_TO`).
8. **`Risk`**: Identified project risks with likelihood, impact, and mitigation strategies.
9. **`Blocker`**: Active impediments with severity and resolution paths.
10. **`Meeting`**: Meeting minutes, attendee registries, and AI summaries.
11. **`ActionItem`**: Tracked action items assigned from meetings or reviews.
12. **`Decision`**: Architectural Decision Records (ADRs) and business decisions.
13. **`ScopeChange`**: Formal change requests tracking schedule and budget impact.
14. **`ApprovalRequest`**: Human-in-the-loop review tickets protecting mutations.
15. **`ProjectEvent`**: Immutable chronological audit event trail.
16. **`Document`**: Project document catalog entry.
17. **`DocumentVersion`**: Revisioned files with hash verification and indexing status.

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.11+ (Python 3.13 supported)
- Git

### 2. Setup Environment
```bash
# Clone the repository
git clone https://github.com/YourOrg/ProgramSaathi.git
cd ProgramSaathi

# Create and activate a virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and populate with configuration:
```bash
cp .env.example .env
```
*(Note: Phase 1 operates completely offline using in-memory fallbacks without requiring live Azure credentials.)*

### 4. Run the Test Suite
```bash
pytest -v
```

### 5. Run the Application Bootstrap
```bash
python -m programsaathi.main
```

---

## 🗺️ Implementation Roadmap

- [x] **Phase 1: Python Foundation & Domain Models** (Current)
  - Full modular directory structure
  - 17 Pydantic domain models with strict validation
  - Configuration management via Pydantic Settings
  - Structured logging & explicit exception hierarchy
  - Service client interfaces (Foundry, Blob, Search, SQL)
  - Repository interfaces with in-memory test doubles
  - Tool registry with human-in-the-loop gating
  - Master Orchestrator bootstrap
  - Complete Azure SQL schema (`schema.sql`)
  - Unit, integration, and security test suites
- [ ] **Phase 2: Azure AI Foundry & Azure OpenAI Client Integration**
- [ ] **Phase 3: Azure SQL Database Connection & Migration Pipeline**
- [ ] **Phase 4: Azure Blob Storage Document Lake**
- [ ] **Phase 5: Document Ingestion, Parsing & Normalization**
- [ ] **Phase 6: Azure AI Search Vector Indexing & Hybrid Retrieval**
- [ ] **Phase 7: Project Intake Capability Workflow**
- [ ] **Phase 8: Meeting Intelligence & Decision Extraction**
- [ ] **Phase 9: Scope Change Analysis & Automated Diff Engine**
- [ ] **Phase 10: Evaluation Harness & Benchmark Suite**
