-- ==============================================================================
-- ProgramSaathi - Initial Seed Data for Testing and Verification
-- ==============================================================================

-- Seed Project
INSERT INTO projects (id, project_key, name, description, status, priority)
VALUES (
    'a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d',
    'PRGMS',
    'ProgramSaathi Core Engine',
    'AI-powered Program & Project Management agent built on Microsoft Azure and Python.',
    'PLANNING',
    'HIGH'
);

-- Seed Stakeholder
INSERT INTO stakeholders (id, name, email, role, is_approver, organization)
VALUES (
    'b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e',
    'Dev Lead',
    'devlead@example.com',
    'Principal Software Architect',
    1,
    'Core Engineering'
);

-- Seed Milestone
INSERT INTO milestones (id, project_id, title, description, target_date, status)
VALUES (
    'c3d4e5f6-a7b8-9c0d-1e2f-3a4b5c6d7e8f',
    'a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d',
    'Phase 1 Architecture Baseline',
    'Python foundational models, configuration, tool boundaries and tests sign-off.',
    '2026-10-15',
    'IN_PROGRESS'
);
