# ProgramSaathi — Technical Architecture Blueprint

## 1. System Vision & Purpose

**ProgramSaathi** is an agentic AI system engineered specifically for Enterprise Program and Project Management. Rather than operating as a chatbot or generic summarizer, ProgramSaathi functions as an active technical program management partner.

---

## 2. Architectural Boundaries & Non-Negotiables

```mermaid
flowchart TD
    subgraph Reasoning ["Reasoning & Intelligence"]
        AOAI["Azure AI Foundry / Azure OpenAI\n(gpt-4o)"]
    end

    subgraph Documents ["Unstructured Document Store"]
        BLOB["Azure Blob Storage\n(Raw PDFs, DOCX, XLSX, Notes)"]
    end

    subgraph Retrieval ["Grounding & Retrieval Engine"]
        AIS["Azure AI Search\n(Hybrid Vector + BM25 Search)"]
    end

    subgraph Authoritative ["Authoritative Project State"]
        ASQL[("Azure SQL Database\n(ACID Project State, Audit Log)")]
    end

    subgraph PythonCore ["Python 3.11+ Core Runtime"]
        ORCH["ProgramSaathi Orchestrator"]
        GUARD["Security & Guardrails Engine"]
        REG["Tool Registry"]
        SVC["Service Layer"]
        REPO["Repository Layer"]
    end

    subgraph HumanGate ["Human-in-the-Loop Governance"]
        HUMAN["Human Project Sponsor / Tech Lead\n(Approval / Rejection)"]
    end

    AOAI -->|Tool Call / Recommendation| ORCH
    ORCH -->|Scan for Injection / Policies| GUARD
    GUARD -->|Validated Tool Params| REG
    REG -->|Read-only Query| REPO
    REG -->|Read-only Search| AIS
    AIS -->|Retrieve Chunks| BLOB
    REG -->|Mutation Proposal| HUMAN
    HUMAN -->|Explicit Sign-off| ORCH
    ORCH -->|Transactional Mutation| REPO
    REPO -->|ACID Persistence| ASQL
```

### Critical Boundaries
1. **Azure OpenAI / Microsoft Foundry**: Reasoning, interpretation, synthesis, and tool selection.
2. **Azure Blob Storage**: Immutable storage for raw uploaded artifacts (PRDs, meeting transcripts, specs).
3. **Azure AI Search**: Retrievable document chunks, embeddings, hybrid keyword+vector index.
4. **Azure SQL**: Authoritative structured project state, work items, and immutable audit event stream.
5. **Python Core**: Orchestration, validation, security guardrails, business rules, tool dispatch.
6. **Human-in-the-Loop**: Absolute authority on consequential state mutations (scope changes, budget changes, roadmap commits).

---

## 3. Human-in-the-Loop State Mutation Cycle

```mermaid
sequenceDiagram
    participant User as Human Lead
    participant Orchestrator as ProgramSaathi Orchestrator
    participant LLM as Azure OpenAI / Foundry
    participant Security as Security Guard
    participant Repos as SQL Repositories

    User->>Orchestrator: "We need to add multi-region disaster recovery to the roadmap"
    Orchestrator->>LLM: Formulate scope change proposal
    LLM-->>Orchestrator: Tool Call: propose_scope_change
    Orchestrator->>Security: Inspect input for SQL injection & policy
    Security-->>Orchestrator: Inspection Passed
    Orchestrator->>Repos: Create ApprovalRequest (Status: PENDING)
    Orchestrator->>Repos: Log ProjectEvent (SCOPE_CHANGE_PROPOSED)
    Orchestrator-->>User: Pending Proposal (Request ID: prop-001) - Awaiting Sign-off
    
    User->>Orchestrator: Approve Request prop-001 with comments
    Orchestrator->>Repos: Commit Scope Change (Status: APPROVED)
    Orchestrator->>Repos: Log ProjectEvent (APPROVAL_APPROVED)
    Orchestrator-->>User: Scope Change Ratified & Persisted in Azure SQL
```

---

## 4. Phase Plan

1. **Phase 1: Python Foundation & Domain Models** (Current)
2. **Phase 2: Configuration & Secret-Safe Environment** (Current)
3. **Phase 3: Azure Foundry / OpenAI Client Integration**
4. **Phase 4: Structured LLM Output Pipelines**
5. **Phase 5: Azure SQL Integration & Migrations**
6. **Phase 6: Blob Storage Document Lake**
7. **Phase 7: Document Extraction & Normalization**
8. **Phase 8: Azure AI Search Hybrid Indexing & RAG Retrieval**
9. **Phase 9: Project Intake Capability Workflow**
10. **Phase 10: Tool-Calling Agent Loop & Human Gate Execution**
