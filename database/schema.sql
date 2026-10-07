-- ==============================================================================
-- ProgramSaathi - Authoritative Azure SQL Database Schema
-- Master State and Audit Persistence
-- ==============================================================================

-- 1. Projects
CREATE TABLE projects (
    id NVARCHAR(36) PRIMARY KEY,
    project_key NVARCHAR(10) NOT NULL UNIQUE,
    name NVARCHAR(150) NOT NULL,
    description NVARCHAR(MAX) NOT NULL,
    status NVARCHAR(30) NOT NULL DEFAULT 'INITIATION',
    priority NVARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    owner_id NVARCHAR(36) NULL,
    start_date DATE NULL,
    target_end_date DATE NULL,
    budget_allocated DECIMAL(18, 2) NULL,
    created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    metadata NVARCHAR(MAX) NULL
);

-- 2. Stakeholders
CREATE TABLE stakeholders (
    id NVARCHAR(36) PRIMARY KEY,
    name NVARCHAR(150) NOT NULL,
    email NVARCHAR(255) NOT NULL UNIQUE,
    role NVARCHAR(100) NOT NULL,
    is_approver BIT NOT NULL DEFAULT 0,
    organization NVARCHAR(150) NULL,
    created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    metadata NVARCHAR(MAX) NULL
);

-- 3. Milestones
CREATE TABLE milestones (
    id NVARCHAR(36) PRIMARY KEY,
    project_id NVARCHAR(36) NOT NULL FOREIGN KEY REFERENCES projects(id) ON DELETE CASCADE,
    title NVARCHAR(200) NOT NULL,
    description NVARCHAR(MAX) NULL,
    target_date DATE NOT NULL,
    actual_completion_date DATE NULL,
    status NVARCHAR(30) NOT NULL DEFAULT 'TODO',
    created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    metadata NVARCHAR(MAX) NULL
);

-- 4. Requirements
CREATE TABLE requirements (
    id NVARCHAR(36) PRIMARY KEY,
    project_id NVARCHAR(36) NOT NULL FOREIGN KEY REFERENCES projects(id) ON DELETE CASCADE,
    code NVARCHAR(50) NOT NULL,
    title NVARCHAR(255) NOT NULL,
    description NVARCHAR(MAX) NOT NULL,
    category NVARCHAR(50) NOT NULL DEFAULT 'Functional',
    priority NVARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    status NVARCHAR(30) NOT NULL DEFAULT 'PROPOSED',
    source_document_id NVARCHAR(36) NULL,
    acceptance_criteria NVARCHAR(MAX) NULL, -- JSON array
    created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    metadata NVARCHAR(MAX) NULL,
    CONSTRAINT UQ_req_project_code UNIQUE(project_id, code)
);

-- 5. User Stories
CREATE TABLE user_stories (
    id NVARCHAR(36) PRIMARY KEY,
    project_id NVARCHAR(36) NOT NULL FOREIGN KEY REFERENCES projects(id) ON DELETE CASCADE,
    requirement_id NVARCHAR(36) NULL FOREIGN KEY REFERENCES requirements(id),
    code NVARCHAR(50) NOT NULL,
    title NVARCHAR(255) NOT NULL,
    as_a NVARCHAR(255) NOT NULL,
    i_want NVARCHAR(MAX) NOT NULL,
    so_that NVARCHAR(MAX) NOT NULL,
    story_points INT NULL,
    priority NVARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    status NVARCHAR(30) NOT NULL DEFAULT 'BACKLOG',
    acceptance_criteria NVARCHAR(MAX) NULL, -- JSON array
    created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    metadata NVARCHAR(MAX) NULL,
    CONSTRAINT UQ_story_project_code UNIQUE(project_id, code)
);

-- 6. Tasks
CREATE TABLE tasks (
    id NVARCHAR(36) PRIMARY KEY,
    project_id NVARCHAR(36) NOT NULL FOREIGN KEY REFERENCES projects(id) ON DELETE CASCADE,
    user_story_id NVARCHAR(36) NULL FOREIGN KEY REFERENCES user_stories(id),
    milestone_id NVARCHAR(36) NULL FOREIGN KEY REFERENCES milestones(id),
    code NVARCHAR(50) NOT NULL,
    title NVARCHAR(255) NOT NULL,
    description NVARCHAR(MAX) NOT NULL,
    assignee_id NVARCHAR(36) NULL FOREIGN KEY REFERENCES stakeholders(id),
    estimated_hours DECIMAL(8, 2) NULL,
    actual_hours DECIMAL(8, 2) NULL,
    priority NVARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    status NVARCHAR(30) NOT NULL DEFAULT 'TODO',
    created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    metadata NVARCHAR(MAX) NULL,
    CONSTRAINT UQ_task_project_code UNIQUE(project_id, code)
);

-- 7. Dependencies
CREATE TABLE dependencies (
    id NVARCHAR(36) PRIMARY KEY,
    project_id NVARCHAR(36) NOT NULL FOREIGN KEY REFERENCES projects(id),
    source_id NVARCHAR(36) NOT NULL,
    source_type NVARCHAR(50) NOT NULL,
    target_id NVARCHAR(36) NOT NULL,
    target_type NVARCHAR(50) NOT NULL,
    dependency_type NVARCHAR(50) NOT NULL DEFAULT 'BLOCKS',
    description NVARCHAR(MAX) NULL,
    created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    metadata NVARCHAR(MAX) NULL
);

-- 8. Risks
CREATE TABLE risks (
    id NVARCHAR(36) PRIMARY KEY,
    project_id NVARCHAR(36) NOT NULL FOREIGN KEY REFERENCES projects(id) ON DELETE CASCADE,
    code NVARCHAR(50) NOT NULL,
    title NVARCHAR(255) NOT NULL,
    description NVARCHAR(MAX) NOT NULL,
    likelihood NVARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    impact NVARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    mitigation_strategy NVARCHAR(MAX) NOT NULL,
    contingency_plan NVARCHAR(MAX) NULL,
    owner_id NVARCHAR(36) NULL FOREIGN KEY REFERENCES stakeholders(id),
    status NVARCHAR(30) NOT NULL DEFAULT 'TODO',
    created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    metadata NVARCHAR(MAX) NULL,
    CONSTRAINT UQ_risk_project_code UNIQUE(project_id, code)
);

-- 9. Blockers
CREATE TABLE blockers (
    id NVARCHAR(36) PRIMARY KEY,
    project_id NVARCHAR(36) NOT NULL FOREIGN KEY REFERENCES projects(id) ON DELETE CASCADE,
    code NVARCHAR(50) NOT NULL,
    title NVARCHAR(255) NOT NULL,
    description NVARCHAR(MAX) NOT NULL,
    blocked_entity_id NVARCHAR(36) NOT NULL,
    blocked_entity_type NVARCHAR(50) NOT NULL,
    severity NVARCHAR(20) NOT NULL DEFAULT 'HIGH',
    status NVARCHAR(30) NOT NULL DEFAULT 'BLOCKED',
    resolution_path NVARCHAR(MAX) NULL,
    owner_id NVARCHAR(36) NULL FOREIGN KEY REFERENCES stakeholders(id),
    created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    metadata NVARCHAR(MAX) NULL
);

-- 10. Meetings
CREATE TABLE meetings (
    id NVARCHAR(36) PRIMARY KEY,
    project_id NVARCHAR(36) NOT NULL FOREIGN KEY REFERENCES projects(id) ON DELETE CASCADE,
    title NVARCHAR(255) NOT NULL,
    meeting_date DATETIMEOFFSET NOT NULL,
    duration_minutes INT NOT NULL DEFAULT 30,
    attendees NVARCHAR(MAX) NULL, -- JSON array
    agenda NVARCHAR(MAX) NULL,
    raw_notes_document_id NVARCHAR(36) NULL,
    summary NVARCHAR(MAX) NULL,
    created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    metadata NVARCHAR(MAX) NULL
);

-- 11. Action Items
CREATE TABLE action_items (
    id NVARCHAR(36) PRIMARY KEY,
    project_id NVARCHAR(36) NOT NULL FOREIGN KEY REFERENCES projects(id) ON DELETE CASCADE,
    meeting_id NVARCHAR(36) NULL FOREIGN KEY REFERENCES meetings(id),
    title NVARCHAR(255) NOT NULL,
    assignee_id NVARCHAR(36) NULL FOREIGN KEY REFERENCES stakeholders(id),
    due_date DATE NULL,
    priority NVARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    status NVARCHAR(30) NOT NULL DEFAULT 'TODO',
    created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    metadata NVARCHAR(MAX) NULL
);

-- 12. Decisions
CREATE TABLE decisions (
    id NVARCHAR(36) PRIMARY KEY,
    project_id NVARCHAR(36) NOT NULL FOREIGN KEY REFERENCES projects(id) ON DELETE CASCADE,
    code NVARCHAR(50) NOT NULL,
    title NVARCHAR(255) NOT NULL,
    context NVARCHAR(MAX) NOT NULL,
    decision_taken NVARCHAR(MAX) NOT NULL,
    rationale NVARCHAR(MAX) NOT NULL,
    consequences NVARCHAR(MAX) NULL,
    decided_by_id NVARCHAR(36) NULL FOREIGN KEY REFERENCES stakeholders(id),
    decided_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    metadata NVARCHAR(MAX) NULL
);

-- 13. Scope Changes
CREATE TABLE scope_changes (
    id NVARCHAR(36) PRIMARY KEY,
    project_id NVARCHAR(36) NOT NULL FOREIGN KEY REFERENCES projects(id) ON DELETE CASCADE,
    code NVARCHAR(50) NOT NULL,
    title NVARCHAR(255) NOT NULL,
    description NVARCHAR(MAX) NOT NULL,
    reason NVARCHAR(MAX) NOT NULL,
    impact_level NVARCHAR(30) NOT NULL DEFAULT 'MODERATE',
    schedule_impact_days INT NOT NULL DEFAULT 0,
    budget_impact DECIMAL(18, 2) NOT NULL DEFAULT 0.0,
    status NVARCHAR(30) NOT NULL DEFAULT 'PENDING',
    proposed_by_id NVARCHAR(36) NULL,
    created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    metadata NVARCHAR(MAX) NULL
);

-- 14. Approval Requests (Human-in-the-Loop Gateway)
CREATE TABLE approval_requests (
    id NVARCHAR(36) PRIMARY KEY,
    project_id NVARCHAR(36) NOT NULL FOREIGN KEY REFERENCES projects(id) ON DELETE CASCADE,
    entity_type NVARCHAR(50) NOT NULL,
    entity_id NVARCHAR(36) NOT NULL,
    action_type NVARCHAR(50) NOT NULL,
    requested_by NVARCHAR(100) NOT NULL DEFAULT 'AI_AGENT',
    summary NVARCHAR(MAX) NOT NULL,
    proposed_diff NVARCHAR(MAX) NOT NULL, -- JSON formatted diff
    status NVARCHAR(30) NOT NULL DEFAULT 'PENDING',
    reviewer_id NVARCHAR(36) NULL FOREIGN KEY REFERENCES stakeholders(id),
    review_comments NVARCHAR(MAX) NULL,
    reviewed_at DATETIMEOFFSET NULL,
    created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    metadata NVARCHAR(MAX) NULL
);

-- 15. Project Events (Immutable Audit Log)
CREATE TABLE project_events (
    id NVARCHAR(36) PRIMARY KEY,
    project_id NVARCHAR(36) NOT NULL FOREIGN KEY REFERENCES projects(id),
    event_type NVARCHAR(100) NOT NULL,
    actor_type NVARCHAR(50) NOT NULL, -- USER, AGENT, SYSTEM
    actor_id NVARCHAR(100) NOT NULL,
    entity_type NVARCHAR(50) NULL,
    entity_id NVARCHAR(36) NULL,
    summary NVARCHAR(MAX) NOT NULL,
    payload NVARCHAR(MAX) NULL, -- JSON formatted event context
    created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    metadata NVARCHAR(MAX) NULL
);

-- 16. Documents
CREATE TABLE documents (
    id NVARCHAR(36) PRIMARY KEY,
    project_id NVARCHAR(36) NOT NULL FOREIGN KEY REFERENCES projects(id) ON DELETE CASCADE,
    title NVARCHAR(255) NOT NULL,
    document_type NVARCHAR(50) NOT NULL DEFAULT 'OTHER',
    latest_version INT NOT NULL DEFAULT 1,
    primary_blob_url NVARCHAR(1024) NULL,
    summary NVARCHAR(MAX) NULL,
    is_active BIT NOT NULL DEFAULT 1,
    created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    metadata NVARCHAR(MAX) NULL
);

-- 17. Document Versions
CREATE TABLE document_versions (
    id NVARCHAR(36) PRIMARY KEY,
    document_id NVARCHAR(36) NOT NULL FOREIGN KEY REFERENCES documents(id) ON DELETE CASCADE,
    version_number INT NOT NULL DEFAULT 1,
    file_name NVARCHAR(255) NOT NULL,
    content_type NVARCHAR(100) NOT NULL,
    file_size_bytes BIGINT NOT NULL DEFAULT 0,
    blob_path NVARCHAR(1024) NOT NULL,
    sha256_hash NVARCHAR(64) NOT NULL,
    uploaded_by NVARCHAR(36) NULL FOREIGN KEY REFERENCES stakeholders(id),
    is_indexed BIT NOT NULL DEFAULT 0,
    chunk_count INT NOT NULL DEFAULT 0,
    created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    updated_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    metadata NVARCHAR(MAX) NULL,
    CONSTRAINT UQ_doc_version UNIQUE(document_id, version_number)
);
